"""Omnia Discuss API — 三方讨论系统核心逻辑"""

from __future__ import annotations

import json
from core.config import OMNIA_HOME
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
WORKSPACE = PROJECT_ROOT.parent

# 讨论会话存储
DISCUSSION_DIR = OMNIA_HOME / "discussions"


def _ensure_discussion_dir():
    """确保讨论目录存在"""
    DISCUSSION_DIR.mkdir(parents=True, exist_ok=True)


def _load_discussion(session_id: str) -> dict:
    """加载讨论会话"""
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
        "status": "waiting",  # waiting, discussing, decided, executed
        "decision": None,
        "executor": None,
        "created_at": datetime.now().isoformat(),
    }


def _save_discussion(session_id: str, data: dict):
    """保存讨论会话"""
    _ensure_discussion_dir()
    file = DISCUSSION_DIR / f"{session_id}.json"
    file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_discuss_system_prompt(round_num: int, previous_opinions: list) -> str:
    """构建讨论用的 system prompt"""
    
    base_prompt = """你是 Omnia，一个 AI 助手。你正在和无限（另一个 AI 助手）以及用户（原点）进行三方讨论。

## 你的身份
- 你是 Omnia，一个深思熟虑的 AI 助手
- 你的任务是提供不同于无限的视角，补充他的建议，或者提出不同的观点
- 你可以同意无限的观点，但需要说明理由
- 你也可以不同意，但需要给出充分的论据

## 讨论规则
1. 每轮你需要针对问题给出你的看法
2. 你需要参考无限在之前轮次的意见
3. 如果无限调整了观点，你应该回应他的调整
4. 保持简洁，每轮回复控制在 200-500 字
5. 不要重复无限已经说过的内容
6. 如果你们观点一致，说明为什么一致
7. 如果观点不同，给出你的理由

## 回复格式
```json
{
  "opinion": "你的看法...",
  "key_points": ["关键点1", "关键点2"],
  "concerns": ["关注点1"],
  "agree_with_infinite": true/false,
  "confidence": 0.8
}
```
"""

    # 添加之前的讨论历史
    if previous_opinions:
        history = "\n\n## 之前的讨论\n"
        for op in previous_opinions:
            history += f"\n**第 {op['round']} 轮 - {op['speaker']}：**\n{op['content']}\n"
        base_prompt += history
    
    return base_prompt


def _call_model_for_discussion(
    question: str,
    round_num: int,
    previous_opinions: list,
    api_key: str,
    provider: str
) -> dict:
    """调用模型生成讨论回复"""
    from omnia.chat import _call_model_messages
    
    system_prompt = _build_discuss_system_prompt(round_num, previous_opinions)
    
    # 构建用户消息
    if round_num == 1:
        user_message = f"用户提出了一个问题：\n\n{question}\n\n请给出你的看法。"
    else:
        # 找到无限最近一轮的意见
        infinite_opinions = [op for op in previous_opinions if op["speaker"] == "infinite"]
        if infinite_opinions:
            last_infinite = infinite_opinions[-1]["content"]
            user_message = f"无限在第 {round_num - 1} 轮调整了他的建议：\n\n{last_infinite}\n\n请基于这个调整，给出你的看法。"
        else:
            user_message = f"这是第 {round_num} 轮讨论，请继续给出你的看法。"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    try:
        data = _call_model_messages(api_key, provider, messages, tools=None)
        reply = data["choices"][0]["message"].get("content", "")
        
        # 尝试解析 JSON
        import re
        # 提取 JSON 块
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', reply, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            # 尝试直接解析
            try:
                result = json.loads(reply)
            except Exception:
                # 如果不是 JSON，构造一个默认结构
                result = {
                    "opinion": reply,
                    "key_points": [],
                    "concerns": [],
                    "agree_with_infinite": None,
                    "confidence": 0.7
                }
        
        return result
    except Exception as e:
        return {
            "opinion": f"[错误] 生成回复失败: {e}",
            "key_points": [],
            "concerns": [],
            "agree_with_infinite": None,
            "confidence": 0.0
        }


# === API 端点处理函数 ===

def handle_start_discussion(data: dict, api_key: str, provider: str) -> dict:
    """开始一个新的讨论会话"""
    import uuid
    
    question = (data.get("question") or "").strip()
    if not question:
        return {"error": "问题不能为空"}, 400
    
    # 生成会话 ID
    session_id = f"discuss_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    # 创建会话
    discussion = _load_discussion(session_id)
    discussion["question"] = question
    discussion["status"] = "discussing"
    discussion["round"] = 0
    _save_discussion(session_id, discussion)
    
    return {
        "session_id": session_id,
        "question": question,
        "status": "ready",
        "message": "讨论会话已创建，等待无限发表意见"
    }


def handle_infinite_opinion(data: dict, api_key: str, provider: str) -> dict:
    """接收无限的意见"""
    session_id = data.get("session_id")
    opinion_content = data.get("opinion")
    
    if not session_id or not opinion_content:
        return {"error": "缺少 session_id 或 opinion"}, 400
    
    discussion = _load_discussion(session_id)
    if not discussion["session_id"]:
        return {"error": "会话不存在"}, 404
    
    # 添加无限的意见
    discussion["round"] += 1
    discussion["opinions"].append({
        "speaker": "infinite",
        "content": opinion_content,
        "round": discussion["round"],
        "timestamp": datetime.now().isoformat()
    })
    _save_discussion(session_id, discussion)
    
    return {
        "session_id": session_id,
        "round": discussion["round"],
        "status": "omnia_turn",
        "message": "无限已发表意见，等待 Omnia 回复"
    }


def handle_omnia_opinion(data: dict, api_key: str, provider: str) -> dict:
    """生成 Omnia 的意见"""
    session_id = data.get("session_id")
    
    if not session_id:
        return {"error": "缺少 session_id"}, 400
    
    discussion = _load_discussion(session_id)
    if not discussion["session_id"]:
        return {"error": "会话不存在"}, 404
    
    if discussion["status"] != "discussing":
        return {"error": "讨论已结束"}, 400
    
    # 获取当前轮次和之前的意见
    current_round = discussion["round"]
    previous_opinions = discussion["opinions"]
    
    # 调用模型生成 Omnia 的意见
    omnia_result = _call_model_for_discussion(
        question=discussion["question"],
        round_num=current_round,
        previous_opinions=previous_opinions,
        api_key=api_key,
        provider=provider
    )
    
    # 添加 Omnia 的意见
    discussion["opinions"].append({
        "speaker": "omnia",
        "content": omnia_result["opinion"],
        "key_points": omnia_result.get("key_points", []),
        "concerns": omnia_result.get("concerns", []),
        "agree_with_infinite": omnia_result.get("agree_with_infinite"),
        "confidence": omnia_result.get("confidence", 0.7),
        "round": current_round,
        "timestamp": datetime.now().isoformat()
    })
    _save_discussion(session_id, discussion)
    
    return {
        "session_id": session_id,
        "round": current_round,
        "speaker": "omnia",
        "opinion": omnia_result["opinion"],
        "key_points": omnia_result.get("key_points", []),
        "concerns": omnia_result.get("concerns", []),
        "agree_with_infinite": omnia_result.get("agree_with_infinite"),
        "confidence": omnia_result.get("confidence", 0.7),
        "status": "waiting_decision",
        "message": "Omnia 已发表意见，等待用户决定"
    }


def handle_next_round(data: dict, api_key: str, provider: str) -> dict:
    """开始下一轮讨论"""
    session_id = data.get("session_id")
    
    if not session_id:
        return {"error": "缺少 session_id"}, 400
    
    discussion = _load_discussion(session_id)
    if not discussion["session_id"]:
        return {"error": "会话不存在"}, 404
    
    if discussion["round"] >= discussion["max_rounds"]:
        return {
            "error": f"已达到最大轮次限制 ({discussion['max_rounds']} 轮)",
            "round": discussion["round"],
            "status": "max_rounds_reached"
        }, 400
    
    return {
        "session_id": session_id,
        "round": discussion["round"] + 1,
        "status": "infinite_turn",
        "message": "等待无限发表新一轮意见"
    }


def handle_make_decision(data: dict) -> dict:
    """用户做出决策"""
    session_id = data.get("session_id")
    decision = data.get("decision")  # "infinite", "omnia", "both", "none"
    executor = data.get("executor")  # "infinite", "omnia", "none"
    
    if not session_id:
        return {"error": "缺少 session_id"}, 400
    
    discussion = _load_discussion(session_id)
    if not discussion["session_id"]:
        return {"error": "会话不存在"}, 404
    
    discussion["status"] = "decided"
    discussion["decision"] = decision
    discussion["executor"] = executor
    discussion["decided_at"] = datetime.now().isoformat()
    _save_discussion(session_id, discussion)
    
    return {
        "session_id": session_id,
        "decision": decision,
        "executor": executor,
        "status": "decided",
        "message": f"已决定采用 {decision} 方案，执行者: {executor}"
    }


def handle_get_discussion(data: dict) -> dict:
    """获取讨论会话状态"""
    session_id = data.get("session_id")
    
    if not session_id:
        return {"error": "缺少 session_id"}, 400
    
    discussion = _load_discussion(session_id)
    if not discussion["session_id"]:
        return {"error": "会话不存在"}, 404
    
    return discussion


def handle_list_discussions() -> dict:
    """列出所有讨论会话"""
    _ensure_discussion_dir()
    sessions = []
    for file in DISCUSSION_DIR.glob("discuss_*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            sessions.append({
                "session_id": data.get("session_id"),
                "question": data.get("question", "")[:50] + "...",
                "round": data.get("round", 0),
                "status": data.get("status"),
                "created_at": data.get("created_at"),
            })
        except Exception:
            pass
    
    return {"sessions": sessions, "total": len(sessions)}
