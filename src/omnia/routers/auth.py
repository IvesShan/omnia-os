"""
Omnia 认证路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
from pathlib import Path

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 用户数据文件
USERS_FILE = Path.home() / ".omnia" / "users.json"


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


def load_users() -> dict:
    """加载用户数据"""
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users: dict) -> bool:
    """保存用户数据"""
    try:
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


@router.post("/login")
async def login(req: LoginRequest):
    """用户登录"""
    users = load_users()
    
    if req.username not in users:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    user = users[req.username]
    if user.get("password") != req.password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    return {
        "ok": True,
        "message": "登录成功",
        "user": {
            "username": req.username,
            "email": user.get("email"),
            "role": user.get("role", "user")
        }
    }


@router.post("/register")
async def register(req: RegisterRequest):
    """用户注册"""
    users = load_users()
    
    if req.username in users:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    users[req.username] = {
        "password": req.password,
        "email": req.email,
        "role": "user"
    }
    
    if save_users(users):
        return {"ok": True, "message": "注册成功"}
    else:
        raise HTTPException(status_code=500, detail="注册失败")


@router.get("/check")
async def check_auth():
    """检查认证状态"""
    return {"ok": True, "message": "认证系统正常"}


