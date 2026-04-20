#!/usr/bin/env python3
"""
同步 OpenClaw Gateway 会话到 Omnia Memory Palace

将 ~/.openclaw/agents/main/sessions/*.jsonl 中的对话记录
同步到 ~/.omnia/memory_palace.db 的 conversation_logs 表。

用法：
    python3 scripts/sync_openclaw_sessions.py [--full]
    
    --full: 全量同步（默认只同步最近7天）
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 配置
OPENCLAW_SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
OMNIA_DB = Path.home() / ".omnia" / "memory_palace.db"
LAST_SYNC_FILE = Path.home() / ".omnia" / ".openclaw_sync_time"

def get_last_sync_time() -> datetime:
    """获取上次同步时间"""
    if LAST_SYNC_FILE.exists():
        try:
            ts = float(LAST_SYNC_FILE.read_text().strip())
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except:
            pass
    # 默认：同步最近7天
    return datetime.now(timezone.utc) - timedelta(days=7)

def save_sync_time():
    """保存本次同步时间"""
    LAST_SYNC_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_SYNC_FILE.write_text(str(datetime.now(timezone.utc).timestamp()))

def parse_jsonl_file(file_path: Path, since: datetime = None) -> list:
    """解析 JSONL 会话文件"""
    messages = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                # 只处理 message 类型的条目
                if entry.get('type') != 'message':
                    continue
                
                # 检查时间
                timestamp_str = entry.get('timestamp', '')
                if timestamp_str:
                    try:
                        # ISO 格式：2026-04-19T06:06:48.183Z
                        entry_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if since and entry_time < since:
                            continue
                    except:
                        pass
                
                msg = entry.get('message', {})
                role = msg.get('role', '')
                content_parts = msg.get('content', [])
                
                # 提取文本内容
                text_content = ""
                for part in content_parts:
                    if isinstance(part, dict):
                        if part.get('type') == 'text':
                            text_content += part.get('text', '')
                        elif part.get('type') == 'thinking':
                            # 跳过 thinking 内容
                            pass
                    elif isinstance(part, str):
                        text_content += part
                
                if text_content and role in ('user', 'assistant'):
                    messages.append({
                        'id': entry.get('id', ''),
                        'session_id': file_path.stem,  # 使用文件名作为 session_id
                        'role': role,
                        'content': text_content,
                        'timestamp': timestamp_str,
                    })
    except Exception as e:
        print(f"  [错误] 解析 {file_path.name}: {e}")
    
    return messages

def sync_to_omnia(messages: list) -> tuple:
    """同步消息到 Omnia Memory Palace"""
    
    if not OMNIA_DB.exists():
        print(f"[错误] Omnia 数据库不存在: {OMNIA_DB}")
        return 0, 0
    
    conn = sqlite3.connect(str(OMNIA_DB))
    cursor = conn.cursor()
    
    inserted = 0
    skipped = 0
    
    for msg in messages:
        # 检查是否已存在（通过 metadata 中的 openclaw_id）
        cursor.execute(
            "SELECT COUNT(*) FROM conversation_logs WHERE metadata LIKE ?",
            (f'%"openclaw_id": "{msg["id"]}"%',)
        )
        if cursor.fetchone()[0] > 0:
            skipped += 1
            continue
        
        # 插入消息
        metadata = json.dumps({
            "openclaw_id": msg["id"],
            "source": "openclaw_gateway",
            "timestamp": msg["timestamp"],
        }, ensure_ascii=False)
        
        try:
            cursor.execute("""
                INSERT INTO conversation_logs 
                (session_id, turn_number, role, content, metadata, created_at)
                VALUES (?, 0, ?, ?, ?, ?)
            """, (
                msg['session_id'],
                msg['role'],
                msg['content'],
                metadata,
                msg['timestamp'] or datetime.now().isoformat(),
            ))
            inserted += 1
        except Exception as e:
            print(f"  [错误] 插入消息失败: {e}")
    
    conn.commit()
    conn.close()
    
    return inserted, skipped

def main():
    full_sync = '--full' in sys.argv
    
    print("=" * 60)
    print("OpenClaw Gateway → Omnia Memory Palace 同步")
    print("=" * 60)
    
    if not OPENCLAW_SESSIONS_DIR.exists():
        print(f"[错误] OpenClaw sessions 目录不存在: {OPENCLAW_SESSIONS_DIR}")
        return
    
    # 获取同步时间范围
    since = None if full_sync else get_last_sync_time()
    if since:
        print(f"[模式] 增量同步（从 {since.isoformat()} 起）")
    else:
        print(f"[模式] 全量同步")
    
    # 获取所有 JSONL 文件
    jsonl_files = sorted(OPENCLAW_SESSIONS_DIR.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)
    print(f"[发现] {len(jsonl_files)} 个会话文件")
    
    total_messages = []
    
    for jsonl_file in jsonl_files:
        # 跳过 .reset 文件
        if '.reset' in jsonl_file.name:
            continue
        
        messages = parse_jsonl_file(jsonl_file, since)
        if messages:
            print(f"  [{jsonl_file.name[:20]}...] {len(messages)} 条消息")
            total_messages.extend(messages)
    
    print(f"\n[总计] {len(total_messages)} 条待同步消息")
    
    if not total_messages:
        print("[完成] 无新消息需要同步")
        return
    
    # 同步到 Omnia
    print(f"\n[同步] 写入 Omnia Memory Palace...")
    inserted, skipped = sync_to_omnia(total_messages)
    
    print(f"\n[结果]")
    print(f"  ✅ 新增: {inserted} 条")
    print(f"  ⏭️  跳过: {skipped} 条（已存在）")
    
    # 保存同步时间
    save_sync_time()
    print(f"\n[完成] 同步时间已保存")

if __name__ == "__main__":
    main()
