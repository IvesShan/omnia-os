"""
讨论系统路由
负责：多 Agent 讨论、决策
集成 discuss_api.py 的核心逻辑
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from src.omnia.config import settings

router = APIRouter()


class DiscussionStartRequest(BaseModel):
    """开始讨论请求"""
    question: str
    max_rounds: int = 3
    context: Optional[str] = None


class DiscussionRoundRequest(BaseModel):
    """讨论轮次请求"""
    session_id: str
    round_num: int
    speaker: str  # "infinite" or "omnia"
    opinion: str
    key_points: Optional[List[str]] = None
    concerns: Optional[List[str]] = None
    confidence: Optional[float] = 0.7


class DecisionRequest(BaseModel):
    """决策请求"""
    session_id: str
    decision: str  # "infinite", "omnia", "both", "none"
    executor: str  # "infinite", "omnia", "none"


# 讨论会话存储
DISCUSSION_DIR = settings.omnia_home / "discussions"


def _ensure_discussion_dir():
    """确保讨论目录存在"""
    DISCUSSION_DIR.mkdir(parents=True, exist_ok=True)


def _load_discussion(session_id: str) -> dict:
    """加载讨论会话"""
    import json
    _ensure_discussion_dir()
    file = DISCUSSION_DIR / f"{session_id}.json"
    if file.exists():
        try:
            return json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "session_id": session_id,
        "question": "",
        "round": 0,
        "max_rounds": 3,
        "opinions": [],
        "status": "waiting",
        "decision": None,
        "executor": None,
        "created_at": datetime.now().isoformat(),
    }


def _save_discussion(session_id: str, data: dict):
    """保存讨论会话"""
    import json
    _ensure_discussion_dir()
    file = DISCUSSION_DIR / f"{session_id}.json"
    file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.post("/discuss/start")
async def start_discussion(req: DiscussionStartRequest) -> dict:
    """
    开始新的三方讨论
    
    创建一个新的讨论会话，Omnia 和 Infinite 将针对问题进行多轮讨论
    """
    import uuid
    
    session_id = f"discuss_{uuid.uuid4().hex[:8]}"
    
    discussion = {
        "session_id": session_id,
        "question": req.question,
        "context": req.context,
        "round": 0,
        "max_rounds": req.max_rounds,
        "opinions": [],
        "status": "waiting",
        "decision": None,
        "executor": None,
        "created_at": datetime.now().isoformat(),
    }
    
    _save_discussion(session_id, discussion)
    
    return {
        "ok": True,
        "session_id": session_id,
        "status": "created",
        "max_rounds": req.max_rounds,
        "message": "讨论会话已创建，等待 Infinite 发表第一轮意见",
        "next_turn": "infinite",
    }


@router.post("/discuss/round")
async def submit_round(req: DiscussionRoundRequest) -> dict:
    """
    提交一轮讨论意见
    
    记录 Infinite 或 Omnia 的意见，并推进讨论进程
    """
    discussion = _load_discussion(req.session_id)
    
    if not discussion.get("question"):
        raise HTTPException(status_code=404, detail="讨论会话不存在")
    
    if discussion["status"] == "decided":
        raise HTTPException(status_code=400, detail="讨论已结束")
    
    # 记录意见
    opinion = {
        "round": req.round_num,
        "speaker": req.speaker,
        "opinion": req.opinion,
        "key_points": req.key_points or [],
        "concerns": req.concerns or [],
        "confidence": req.confidence,
        "timestamp": datetime.now().isoformat(),
    }
    
    discussion["opinions"].append(opinion)
    discussion["round"] = req.round_num
    
    # 判断下一个发言者
    if req.speaker == "infinite":
        next_turn = "omnia"
        status = "omnia_turn"
    else:
        # Omnia 发言后，检查是否达到最大轮次
        if req.round_num >= discussion["max_rounds"]:
            next_turn = "user"
            status = "waiting_decision"
        else:
            next_turn = "infinite"
            status = "infinite_turn"
            discussion["round"] = req.round_num + 1
    
    discussion["status"] = status
    _save_discussion(req.session_id, discussion)
    
    return {
        "ok": True,
        "session_id": req.session_id,
        "round": req.round_num,
        "speaker": req.speaker,
        "status": status,
        "next_turn": next_turn,
        "message": f"{req.speaker} 的意见已记录",
    }


@router.post("/discuss/decision")
async def make_decision(req: DecisionRequest) -> dict:
    """
    用户做出决策
    
    选择采用哪个 Agent 的方案，并指定执行者
    """
    discussion = _load_discussion(req.session_id)
    
    if not discussion.get("question"):
        raise HTTPException(status_code=404, detail="讨论会话不存在")
    
    discussion["status"] = "decided"
    discussion["decision"] = req.decision
    discussion["executor"] = req.executor
    discussion["decided_at"] = datetime.now().isoformat()
    
    _save_discussion(req.session_id, discussion)
    
    return {
        "ok": True,
        "session_id": req.session_id,
        "decision": req.decision,
        "executor": req.executor,
        "status": "decided",
        "message": f"已决定采用 {req.decision} 方案，执行者: {req.executor}",
    }


@router.get("/discuss/{session_id}")
async def get_discussion(session_id: str) -> dict:
    """获取讨论会话详情"""
    discussion = _load_discussion(session_id)
    
    if not discussion.get("question"):
        raise HTTPException(status_code=404, detail="讨论会话不存在")
    
    return discussion


@router.get("/discuss")
async def list_discussions() -> dict:
    """列出所有讨论会话"""
    import json
    
    _ensure_discussion_dir()
    sessions = []
    
    for file in DISCUSSION_DIR.glob("discuss_*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            sessions.append({
                "session_id": data["session_id"],
                "question": data["question"][:100],
                "round": data["round"],
                "status": data["status"],
                "created_at": data["created_at"],
            })
        except (json.JSONDecodeError, OSError, KeyError):
            continue
    
    return {
        "total": len(sessions),
        "sessions": sorted(sessions, key=lambda x: x["created_at"], reverse=True),
    }


@router.delete("/discuss/{session_id}")
async def delete_discussion(session_id: str) -> dict:
    """删除讨论会话"""
    file = DISCUSSION_DIR / f"{session_id}.json"
    
    if not file.exists():
        raise HTTPException(status_code=404, detail="讨论会话不存在")
    
    file.unlink()
    
    return {
        "ok": True,
        "message": f"讨论会话 {session_id} 已删除",
    }
