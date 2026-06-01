"""
Omnia 在线激活服务器 v1.0
=========================
轻量级 FastAPI 服务，处理卡密激活、验证、撤销、统计

部署方式：uvicorn server.activation_server:app --host 0.0.0.0 --port 8900
"""

import hashlib
import json
import os
import platform
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ============================================================
# 配置
# ============================================================

MASTER_KEY = "Omnia-Commercial-License-2026-SecretKey-v3"
DB_PATH = Path(__file__).parent / "activations.db"
ADMIN_TOKEN = os.getenv("OMNIA_ADMIN_TOKEN", "omnia-admin-2026-secret")

# 授权类型（与客户端一致）
LICENSE_TYPES = {
    "T": {"type": "trial", "days": 1, "label": "试用版", "max_devices": 1},
    "M": {"type": "monthly", "days": 30, "label": "月卡", "max_devices": 1},
    "Q": {"type": "quarterly", "days": 90, "label": "季卡", "max_devices": 1},
    "Y": {"type": "yearly", "days": 365, "label": "年卡", "max_devices": 2},
    "P": {"type": "perpetual", "days": 36500, "label": "终身版", "max_devices": 3},
}

# 离线宽限期（天）
OFFLINE_GRACE_DAYS = 7

# 不易混淆字符集（与客户端一致）
CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

# ============================================================
# 数据库
# ============================================================

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    # 卡密表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS license_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE NOT NULL,
            license_type TEXT NOT NULL,
            type_label TEXT NOT NULL,
            days INTEGER NOT NULL,
            max_devices INTEGER DEFAULT 1,
            is_revoked INTEGER DEFAULT 0,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            created_by TEXT DEFAULT 'admin'
        )
    """)

    # 激活记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            machine_name TEXT DEFAULT '',
            os_type TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            activated_at TEXT NOT NULL,
            last_verify_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            UNIQUE(license_key, machine_id)
        )
    """)

    # 事件日志表（统计用）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            license_key TEXT DEFAULT '',
            machine_id TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            extra TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        )
    """)

    # 索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_keys_key ON license_keys(license_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_key ON activations(license_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_act_machine ON activations(machine_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON events(created_at)")

    conn.commit()
    conn.close()


# ============================================================
# 工具函数
# ============================================================

def log_event(event_type: str, license_key: str = "", machine_id: str = "",
              ip: str = "", extra: dict = None):
    """记录事件"""
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO events (event_type, license_key, machine_id, ip_address, extra, created_at) VALUES (?,?,?,?,?,?)",
            (event_type, license_key, machine_id, ip, json.dumps(extra or {}), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def verify_key_signature(key: str) -> tuple[bool, str]:
    """验证卡密签名（与客户端一致）"""
    try:
        clean = key.strip().upper()
        if clean.startswith("OMNI-"):
            clean = clean[5:]
        clean = clean.replace("-", "").replace(" ", "")

        if len(clean) != 16:
            return False, ""

        random_part = clean[:12]
        type_char = clean[12]
        signature = clean[13:]

        if type_char not in LICENSE_TYPES:
            return False, ""

        # 验证签名
        sig_data = f"{random_part}{type_char}{MASTER_KEY}"
        expected_sig = hashlib.sha256(sig_data.encode()).hexdigest()[:3].upper()

        if signature != expected_sig:
            return False, ""

        return True, type_char
    except Exception:
        return False, ""


def get_client_ip(request: Request) -> str:
    """获取客户端 IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ============================================================
# Pydantic 模型
# ============================================================

class ActivateRequest(BaseModel):
    license_key: str
    machine_id: str
    machine_name: str = ""
    os_type: str = ""

class VerifyRequest(BaseModel):
    license_key: str
    machine_id: str

class DeactivateRequest(BaseModel):
    license_key: str
    machine_id: str

class BatchGenerateRequest(BaseModel):
    license_type: str  # T/M/Q/Y/P
    count: int = 10
    note: str = ""

class RevokeRequest(BaseModel):
    license_key: str

# ============================================================
# FastAPI 应用
# ============================================================

app = FastAPI(title="Omnia Activation Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()
    print(f"🚀 Omnia Activation Server started")
    print(f"📊 Database: {DB_PATH}")


# ============================================================
# 公开 API（供客户端调用）
# ============================================================

@app.post("/api/v1/activate")
async def activate_license(req: ActivateRequest, request: Request):
    """激活卡密"""
    ip = get_client_ip(request)

    # 1. 验证卡密签名
    is_valid, type_char = verify_key_signature(req.license_key)
    if not is_valid:
        log_event("activate_fail", req.license_key, req.machine_id, ip, {"reason": "invalid_signature"})
        raise HTTPException(status_code=400, detail="卡密无效或签名错误")

    license_type = LICENSE_TYPES[type_char]

    conn = get_db()
    try:
        # 2. 检查卡密是否存在（如果不存在则自动注册）
        row = conn.execute("SELECT * FROM license_keys WHERE license_key = ?", (req.license_key,)).fetchone()
        if not row:
            # 自动注册卡密到数据库
            conn.execute(
                """INSERT INTO license_keys (license_key, license_type, type_label, days, max_devices, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (req.license_key, type_char, license_type["label"], license_type["days"],
                 license_type["max_devices"], datetime.now().isoformat())
            )
            conn.commit()
        else:
            # 检查是否被撤销
            if row["is_revoked"]:
                log_event("activate_fail", req.license_key, req.machine_id, ip, {"reason": "revoked"})
                raise HTTPException(status_code=403, detail="该卡密已被撤销")

        # 3. 检查该机器是否已激活
        existing = conn.execute(
            "SELECT * FROM activations WHERE license_key = ? AND machine_id = ? AND is_active = 1",
            (req.license_key, req.machine_id)
        ).fetchone()

        if existing:
            # 已激活，更新最后验证时间
            conn.execute(
                "UPDATE activations SET last_verify_at = ?, machine_name = ?, os_type = ? WHERE id = ?",
                (datetime.now().isoformat(), req.machine_name, req.os_type, existing["id"])
            )
            conn.commit()
            log_event("activate_reuse", req.license_key, req.machine_id, ip)

            activated_at = datetime.fromisoformat(existing["activated_at"])
            expire_at = activated_at + timedelta(days=license_type["days"])
            return {
                "success": True,
                "message": "已激活（重新验证）",
                "type": license_type["type"],
                "type_label": license_type["label"],
                "expire_at": expire_at.strftime("%Y-%m-%d %H:%M:%S"),
                "remaining_days": max(0, (expire_at - datetime.now()).days),
                "offline_grace_days": OFFLINE_GRACE_DAYS,
            }

        # 4. 检查设备数限制
        active_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM activations WHERE license_key = ? AND is_active = 1",
            (req.license_key,)
        ).fetchone()["cnt"]

        if active_count >= license_type["max_devices"]:
            log_event("activate_fail", req.license_key, req.machine_id, ip, {"reason": "max_devices"})
            raise HTTPException(
                status_code=403,
                detail=f"已达到最大设备数限制（{license_type['max_devices']}台），请先在其他设备停用"
            )

        # 5. 执行激活
        now = datetime.now()
        expire_at = now + timedelta(days=license_type["days"])

        conn.execute(
            """INSERT INTO activations (license_key, machine_id, machine_name, os_type, ip_address, activated_at, last_verify_at, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (req.license_key, req.machine_id, req.machine_name, req.os_type, ip, now.isoformat(), now.isoformat())
        )
        conn.commit()

        log_event("activate_success", req.license_key, req.machine_id, ip, {"type": license_type["type"]})

        return {
            "success": True,
            "message": "激活成功",
            "type": license_type["type"],
            "type_label": license_type["label"],
            "expire_at": expire_at.strftime("%Y-%m-%d %H:%M:%S"),
            "remaining_days": max(0, (expire_at - now).days),
            "offline_grace_days": OFFLINE_GRACE_DAYS,
        }

    finally:
        conn.close()


@app.post("/api/v1/verify")
async def verify_license(req: VerifyRequest, request: Request):
    """在线验证授权状态（客户端定期调用）"""
    ip = get_client_ip(request)

    # 验证签名
    is_valid, type_char = verify_key_signature(req.license_key)
    if not is_valid:
        raise HTTPException(status_code=400, detail="卡密无效")

    conn = get_db()
    try:
        # 查找激活记录
        activation = conn.execute(
            "SELECT * FROM activations WHERE license_key = ? AND machine_id = ? AND is_active = 1",
            (req.license_key, req.machine_id)
        ).fetchone()

        if not activation:
            log_event("verify_fail", req.license_key, req.machine_id, ip, {"reason": "not_activated"})
            return {"valid": False, "reason": "not_activated", "message": "未在此设备激活，请先激活"}

        # 检查卡密是否被撤销
        key_row = conn.execute(
            "SELECT is_revoked FROM license_keys WHERE license_key = ?", (req.license_key,)
        ).fetchone()

        if key_row and key_row["is_revoked"]:
            # 撤销激活
            conn.execute("UPDATE activations SET is_active = 0 WHERE license_key = ?", (req.license_key,))
            conn.commit()
            log_event("verify_revoked", req.license_key, req.machine_id, ip)
            return {"valid": False, "reason": "revoked", "message": "该卡密已被撤销"}

        # 计算到期时间
        license_type = LICENSE_TYPES.get(type_char, {"days": 1, "type": "unknown", "label": "未知"})
        activated_at = datetime.fromisoformat(activation["activated_at"])
        expire_at = activated_at + timedelta(days=license_type["days"])
        remaining_days = max(0, (expire_at - datetime.now()).days)

        # 更新最后验证时间
        conn.execute(
            "UPDATE activations SET last_verify_at = ? WHERE id = ?",
            (datetime.now().isoformat(), activation["id"])
        )
        conn.commit()

        log_event("verify", req.license_key, req.machine_id, ip)

        if remaining_days <= 0:
            return {
                "valid": False,
                "reason": "expired",
                "message": "授权已过期，请续费",
                "expire_at": expire_at.strftime("%Y-%m-%d %H:%M:%S"),
                "remaining_days": 0,
            }

        return {
            "valid": True,
            "type": license_type["type"],
            "type_label": license_type["label"],
            "expire_at": expire_at.strftime("%Y-%m-%d %H:%M:%S"),
            "remaining_days": remaining_days,
            "offline_grace_days": OFFLINE_GRACE_DAYS,
            "last_verify": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    finally:
        conn.close()


@app.post("/api/v1/deactivate")
async def deactivate_license(req: DeactivateRequest, request: Request):
    """停用设备（设备迁移）"""
    ip = get_client_ip(request)

    conn = get_db()
    try:
        result = conn.execute(
            "UPDATE activations SET is_active = 0 WHERE license_key = ? AND machine_id = ? AND is_active = 1",
            (req.license_key, req.machine_id)
        )
        conn.commit()

        if result.rowcount > 0:
            log_event("deactivate", req.license_key, req.machine_id, ip)
            return {"success": True, "message": "设备已停用，可在其他设备激活"}
        else:
            return {"success": False, "message": "未找到该设备的激活记录"}
    finally:
        conn.close()


@app.get("/api/v1/status")
async def server_status():
    """服务器状态检查"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "server_time": datetime.now().isoformat(),
        "offline_grace_days": OFFLINE_GRACE_DAYS,
    }


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """管理后台页面"""
    template_path = Path(__file__).parent / "templates" / "admin-dashboard.html"
    if template_path.exists():
        return HTMLResponse(template_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>管理后台模板不存在</h1>", status_code=404)


# ============================================================
# 管理 API（需要 Admin Token）
# ============================================================

def check_admin_token(request: Request):
    """验证管理员 Token"""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="管理员认证失败")


@app.get("/api/v1/admin/stats")
async def admin_stats(request: Request):
    """统计概览"""
    check_admin_token(request)

    conn = get_db()
    try:
        # 总卡密数
        total_keys = conn.execute("SELECT COUNT(*) as cnt FROM license_keys").fetchone()["cnt"]
        active_keys = conn.execute(
            "SELECT COUNT(DISTINCT license_key) as cnt FROM activations WHERE is_active = 1"
        ).fetchone()["cnt"]

        # 总激活设备数
        active_devices = conn.execute(
            "SELECT COUNT(*) as cnt FROM activations WHERE is_active = 1"
        ).fetchone()["cnt"]
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 今日激活数
        today_activations = conn.execute(
            "SELECT COUNT(*) as cnt FROM activations WHERE activated_at LIKE ?",
            (f"{today_str}%",)
        ).fetchone()["cnt"]

        # 今日事件数
        today_events = conn.execute(
            "SELECT COUNT(*) as cnt FROM events WHERE created_at LIKE ?",
            (f"{today_str}%",)
        ).fetchone()["cnt"]

        # 按类型统计
        type_stats = {}
        for row in conn.execute("""
            SELECT lk.license_type, lk.type_label, COUNT(DISTINCT a.license_key) as key_count, COUNT(a.id) as device_count
            FROM license_keys lk
            LEFT JOIN activations a ON lk.license_key = a.license_key AND a.is_active = 1
            GROUP BY lk.license_type
        """).fetchall():
            type_stats[row["license_type"]] = {
                "label": row["type_label"],
                "keys": row["key_count"],
                "devices": row["device_count"],
            }

        # 最近7天激活趋势
        trend = []
        for i in range(6, -1, -1):
            day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM activations WHERE activated_at LIKE ?",
                (f"{day}%",)
            ).fetchone()["cnt"]
            trend.append({"date": day, "count": count})

        # 按操作系统统计
        os_stats = {}
        for row in conn.execute("""
            SELECT os_type, COUNT(*) as cnt FROM activations
            WHERE is_active = 1 AND os_type != ''
            GROUP BY os_type
        """).fetchall():
            os_stats[row["os_type"]] = row["cnt"]

        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "active_devices": active_devices,
            "today_activations": today_activations,
            "today_events": today_events,
            "type_stats": type_stats,
            "os_stats": os_stats,
            "trend_7d": trend,
        }

    finally:
        conn.close()


@app.get("/api/v1/admin/keys")
async def admin_list_keys(request: Request, page: int = 1, size: int = 50):
    """列出卡密"""
    check_admin_token(request)

    conn = get_db()
    try:
        offset = (page - 1) * size
        rows = conn.execute(
            "SELECT * FROM license_keys ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (size, offset)
        ).fetchall()

        total = conn.execute("SELECT COUNT(*) as cnt FROM license_keys").fetchone()["cnt"]

        keys = []
        for row in rows:
            active_devices = conn.execute(
                "SELECT COUNT(*) as cnt FROM activations WHERE license_key = ? AND is_active = 1",
                (row["license_key"],)
            ).fetchone()["cnt"]

            keys.append({
                "license_key": row["license_key"],
                "type": row["license_type"],
                "label": row["type_label"],
                "days": row["days"],
                "max_devices": row["max_devices"],
                "active_devices": active_devices,
                "is_revoked": bool(row["is_revoked"]),
                "note": row["note"],
                "created_at": row["created_at"],
            })

        return {"total": total, "page": page, "size": size, "keys": keys}

    finally:
        conn.close()


@app.get("/api/v1/admin/activations")
async def admin_list_activations(request: Request, page: int = 1, size: int = 50):
    """列出激活记录"""
    check_admin_token(request)

    conn = get_db()
    try:
        offset = (page - 1) * size
        rows = conn.execute(
            "SELECT * FROM activations ORDER BY activated_at DESC LIMIT ? OFFSET ?",
            (size, offset)
        ).fetchall()

        total = conn.execute("SELECT COUNT(*) as cnt FROM activations").fetchone()["cnt"]

        return {
            "total": total,
            "page": page,
            "size": size,
            "activations": [dict(row) for row in rows],
        }

    finally:
        conn.close()


@app.get("/api/v1/admin/events")
async def admin_list_events(request: Request, page: int = 1, size: int = 100,
                            event_type: str = ""):
    """列出事件日志"""
    check_admin_token(request)

    conn = get_db()
    try:
        offset = (page - 1) * size

        if event_type:
            rows = conn.execute(
                "SELECT * FROM events WHERE event_type = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (event_type, size, offset)
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM events WHERE event_type = ?", (event_type,)
            ).fetchone()["cnt"]
        else:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (size, offset)
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) as cnt FROM events").fetchone()["cnt"]

        return {
            "total": total,
            "page": page,
            "size": size,
            "events": [dict(row) for row in rows],
        }

    finally:
        conn.close()


@app.post("/api/v1/admin/generate")
async def admin_generate_keys(req: BatchGenerateRequest, request: Request):
    """批量生成卡密"""
    check_admin_token(request)

    if req.license_type not in LICENSE_TYPES:
        raise HTTPException(status_code=400, detail=f"无效的授权类型: {req.license_type}")

    if req.count < 1 or req.count > 1000:
        raise HTTPException(status_code=400, detail="单次生成数量 1-1000")

    type_info = LICENSE_TYPES[req.license_type]
    generated = []

    conn = get_db()
    try:
        for _ in range(req.count):
            # 生成卡密
            type_char = req.license_type
            random_part = ''.join(secrets.choice(CHARSET) for _ in range(12))
            sig_data = f"{random_part}{type_char}{MASTER_KEY}"
            signature = hashlib.sha256(sig_data.encode()).hexdigest()[:3].upper()
            key_body = f"{random_part}{type_char}{signature}"
            key = f"OMNI-{key_body[:4]}-{key_body[4:8]}-{key_body[8:12]}-{key_body[12:16]}"

            # 存入数据库
            try:
                conn.execute(
                    """INSERT INTO license_keys (license_key, license_type, type_label, days, max_devices, note, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (key, req.license_type, type_info["label"], type_info["days"],
                     type_info["max_devices"], req.note, datetime.now().isoformat())
                )
                generated.append(key)
            except sqlite3.IntegrityError:
                continue  # 重复则跳过

        conn.commit()

        log_event("admin_generate", "", "", "", {"type": req.license_type, "count": len(generated)})

        return {
            "success": True,
            "generated": len(generated),
            "type": type_info["label"],
            "keys": generated,
        }

    finally:
        conn.close()


@app.post("/api/v1/admin/revoke")
async def admin_revoke_key(req: RevokeRequest, request: Request):
    """撤销卡密"""
    check_admin_token(request)

    conn = get_db()
    try:
        # 标记撤销
        result = conn.execute(
            "UPDATE license_keys SET is_revoked = 1 WHERE license_key = ?",
            (req.license_key,)
        )

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="卡密不存在")

        # 停用所有激活
        conn.execute(
            "UPDATE activations SET is_active = 0 WHERE license_key = ?",
            (req.license_key,)
        )
        conn.commit()

        log_event("admin_revoke", req.license_key, "", "")

        return {"success": True, "message": f"卡密已撤销，所有设备已停用"}

    finally:
        conn.close()


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Omnia Activation Server v1.0")
    print("=" * 50)
    print(f"Database: {DB_PATH}")
    print(f"Admin Token: {ADMIN_TOKEN[:8]}...")
    print(f"API Docs: http://localhost:8900/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8900, log_level="info")
