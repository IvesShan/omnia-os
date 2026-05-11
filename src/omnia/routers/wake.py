"""Wake 路由 - Omnia 唤醒功能

支持 Omnia 的完整唤醒序列：
- 加载记忆上下文
- 加载工作记忆
- 加载当前任务
- 加载 IDE 上下文
- 匹配技能
- 构建完整提示
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/wake", tags=["Wake"])


# ========== 请求/响应模型 ==========

class WakeRequest(BaseModel):
    """唤醒请求"""
    message: str
    session_id: Optional[str] = None
    load_memory: bool = True
    load_skills: bool = True
    load_ide_context: bool = True


class WakeResponse(BaseModel):
    """唤醒响应"""
    status: str
    context: Dict[str, Any]
    system_prompt: str
    matched_skills: List[Dict[str, Any]]
    notifications: List[Dict[str, Any]]


# ========== 路由端点 ==========

@router.post("/up")
async def wake_up(request: WakeRequest):
    """
    完整唤醒序列
    
    执行 Omnia 的完整初始化流程：
    1. 加载记忆上下文
    2. 加载工作记忆
    3. 加载当前任务
    4. 加载 IDE 上下文
    5. 匹配技能
    6. 构建系统提示
    """
    try:
        from src.omnia.wake import build_wake_context
        from src.omnia.config import settings
        
        # 构建唤醒上下文
        context = build_wake_context(
            message=request.message,
            session_id=request.session_id,
            load_memory=request.load_memory,
            load_skills=request.load_skills,
            load_ide_context=request.load_ide_context
        )
        
        return {
            "ok": True,
            "status": "awake",
            "context": context.get("context", {}),
            "system_prompt": context.get("system_prompt", ""),
            "matched_skills": context.get("matched_skills", []),
            "notifications": context.get("notifications", [])
        }
    except Exception as e:
        logger.error(f"Wake up failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context")
async def get_wake_context(session_id: Optional[str] = None):
    """获取唤醒上下文（不触发完整唤醒）"""
    try:
        from core.working_memory import load_working_memory, load_current_task
        from src.omnia.config import settings
        
        # 加载工作记忆
        working_memory = load_working_memory()
        
        # 加载当前任务
        current_task = load_current_task()
        
        # 加载 IDE 上下文
        ide_context = None
        ide_path = settings.omnia_home / "ide_context.json"
        if ide_path.exists():
            import json
            try:
                ide_context = json.loads(ide_path.read_text())
            except:
                pass
        
        return {
            "ok": True,
            "working_memory": working_memory,
            "current_task": current_task,
            "ide_context": ide_context
        }
    except Exception as e:
        logger.error(f"Get wake context failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills")
async def get_available_skills():
    """获取所有可用技能"""
    try:
        from pathlib import Path
        import json
        
        skills_dir = Path("/home/shan/omnia-os/skills")
        skills = []
        
        # 扫描技能目录
        for skill_path in skills_dir.rglob("SKILL.md"):
            skill_id = skill_path.parent.name
            try:
                content = skill_path.read_text(encoding="utf-8")
                # 提取描述（第一行或第一个标题）
                lines = content.split("\n")
                description = ""
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        description = line[:200]
                        break
                    elif line.startswith("# "):
                        description = line[2:200]
                        break
                
                skills.append({
                    "id": skill_id,
                    "description": description,
                    "path": str(skill_path)
                })
            except Exception as e:
                logger.warning(f"Failed to load skill {skill_id}: {e}")
        
        return {
            "ok": True,
            "skills": skills,
            "count": len(skills)
        }
    except Exception as e:
        logger.error(f"Get skills failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/clear")
async def clear_notifications(session_id: str):
    """清除会话通知"""
    try:
        from core.neuro_center.notification_queue import pop_notifications_for_session
        
        notifications = pop_notifications_for_session(session_id)
        
        return {
            "ok": True,
            "cleared_count": len(notifications),
            "notifications": notifications
        }
    except Exception as e:
        logger.error(f"Clear notifications failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/persona")
async def get_current_persona():
    """获取当前人格设定"""
    try:
        from core.personas import load_persona
        
        persona = load_persona()
        
        return {
            "ok": True,
            "persona": persona
        }
    except Exception as e:
        logger.error(f"Get persona failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick")
async def quick_wake(message: str = ""):
    """
    快速唤醒 - 最小化上下文加载
    
    只加载必要的上下文，快速响应。
    """
    try:
        from core.memory_palace import MemoryPalace
        from src.omnia.config import settings
        
        # 只加载最近的记忆
        mp = MemoryPalace(db_path=str(settings.memory_palace_db))
        recent = mp.search(message or "recent", limit=3)
        
        return {
            "ok": True,
            "status": "quick_wake",
            "recent_memories": [
                {"content": m.get("content", "")[:200], "score": m.get("score", 0)}
                for m in recent
            ]
        }
    except Exception as e:
        logger.error(f"Quick wake failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
