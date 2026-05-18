"""
确认操作路由
负责：PlanExecutor 确认、单工具确认、确认后消息处理

从 Flask 版 web_server.py 完整移植，保持功能一致性。
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.omnia.config import settings
from src.omnia.config import settings

router = APIRouter()

# ========== 持久化存储 ==========

PENDING_CONF_PATH = settings.pending_conf_path
_pending_lock = threading.Lock()


def _load_pending() -> Dict[str, Dict]:
    """加载待确认的操作"""
    if PENDING_CONF_PATH.exists():
        try:
            return json.loads(PENDING_CONF_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[_load_pending] Failed to load {PENDING_CONF_PATH}: {e}")
    return {}


def _save_pending(data: Dict[str, Dict]) -> None:
    """保存待确认的操作"""
    PENDING_CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PENDING_CONF_PATH.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(PENDING_CONF_PATH)
    except OSError as e:
        print(f"[_save_pending] Failed to save {PENDING_CONF_PATH}: {e}")
        raise


def store_confirmation(cid: str, ctx: Dict) -> None:
    """存储待确认操作（供外部调用）"""
    with _pending_lock:
        data = _load_pending()
        data[cid] = ctx
        _save_pending(data)
        print(f"[store_confirmation] Stored cid={cid}, total_keys={len(data)}")


def pop_confirmation(cid: str) -> Optional[Dict]:
    """弹出待确认操作（供外部调用）"""
    cid = (cid or "").strip()
    if not cid:
        print("[pop_confirmation] Empty cid received")
        return None
    with _pending_lock:
        data = _load_pending()
        ctx = data.pop(cid, None)
        if ctx:
            _save_pending(data)
            print(f"[pop_confirmation] Popped cid={cid}, remaining={len(data)}")
        else:
            print(f"[pop_confirmation] Miss cid={cid}, available_keys={list(data.keys())}")
        return ctx


# ========== 请求/响应模型 ==========

class ConfirmRequest(BaseModel):
    """确认请求"""
    confirm_id: str
    approved: bool


class ConfirmResponse(BaseModel):
    """确认响应"""
    reply: str
    steps: List[Dict[str, Any]] = []


class PendingListResponse(BaseModel):
    """待确认列表响应"""
    pending: List[Dict[str, Any]]
    count: int


# ========== 路由 ==========

@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_action(req: ConfirmRequest):
    """
    确认操作 — 完整版

    支持：
    1. PlanExecutor 确认（多步骤任务）
    2. 单工具确认
    3. 确认后消息处理 + LLM 自然语言回复
    """
    cid = req.confirm_id.strip()
    approved = req.approved

    print(f"[confirm] received cid='{cid}', approved={approved}")

    ctx = pop_confirmation(cid)
    if not ctx:
        raise HTTPException(
            status_code=404,
            detail="无效的确认 ID 或已过期"
        )

    # ===== 拒绝操作 =====
    if not approved:
        if ctx.get("type") == "plan_executor":
            step_name = ctx['steps'][ctx['current_step_index']]['tool_name']
            return ConfirmResponse(
                reply=f"[已取消] 未执行 Plan 步骤 `{step_name}`，整个任务已中止。",
                steps=[]
            )
        return ConfirmResponse(
            reply=f"[已取消] 未执行 {ctx.get('tool_name', '未知工具')}。",
            steps=[]
        )

    # ===== PlanExecutor 确认 =====
    if ctx.get("type") == "plan_executor":
        return await _handle_plan_executor_confirm(ctx)

    # ===== 单工具确认 =====
    return await _handle_single_tool_confirm(ctx)


async def _handle_plan_executor_confirm(ctx: Dict) -> ConfirmResponse:
    """处理 PlanExecutor 确认"""
    try:
        from src.core.actuator.plan_executor import ExecutionPlan, PlanExecutor, Step

        executor = PlanExecutor(ctx["api_key"], ctx["provider"])
        steps = [
            Step(
                id=s["id"],
                description=s["description"],
                tool_name=s["tool_name"],
                tool_args=s["tool_args"],
                result=s.get("result"),
                status=s["status"],
                observation=s["observation"],
            )
            for s in ctx["steps"]
        ]
        plan = ExecutionPlan(goal=ctx["goal"], steps=steps, context=ctx["context"])
        start_idx = ctx["current_step_index"]

        result = executor.resume_from_step(plan, start_idx)
        return ConfirmResponse(
            reply=result["reply"],
            steps=result["steps"]
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_single_tool_confirm(ctx: Dict) -> ConfirmResponse:
    """处理单工具确认"""
    fn_name = ctx.get("tool_name", "unknown")
    fn_args = ctx.get("tool_args", {})

    # ===== 执行工具 =====
    try:
        from src.omnia.services.tool_registry import tool_registry
        raw_result = await tool_registry.execute(fn_name, fn_args)
        # 提取 result 字段
        if isinstance(raw_result, dict) and "result" in raw_result:
            result = raw_result["result"]
        else:
            result = raw_result
    except Exception as e:
        result = {"error": str(e)}

    # ===== 压缩结果 =====
    result_json = json.dumps(result, ensure_ascii=False)
    if len(result_json) > 1500:
        try:
            from src.core.cognition.context_compressor import ContextCompressor
            result_json = ContextCompressor().compress(result_json).summary
        except Exception:
            result_json = result_json[:1500] + "...(已截断)"

    # ===== 构建工具结果消息 =====
    step = {
        "tool": fn_name,
        "arguments": fn_args,
        "result_summary": str(result)[:200]
    }

    tool_call_id = ctx.get("tool_call_id", "confirm_call")
    new_messages = ctx.get("messages", []) + [
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": fn_name,
            "content": result_json,
        }
    ]

    # 添加指令：要求模型生成自然语言回复
    new_messages.append({
        "role": "system",
        "content": "工具已执行完成。现在请用自然语言总结结果并回答用户的问题。不要输出任何工具调用格式。"
    })

    # ===== 调用 LLM 生成自然语言回复 =====
    try:
        from src.omnia.services.llm_client import LLMClient
        from src.omnia.config import settings

        client = LLMClient()
        provider = ctx.get("provider") or settings.current_provider or "deepseek"

        llm_result = await client.call(
            messages=new_messages,
            provider=provider,
            tools=None,  # 禁止再次工具调用
        )

        reply = llm_result.get("content", "")

        # 清理可能的工具调用格式
        if re.match(r'^\w+\s*\n?\s*\{', reply):
            match = re.match(r'^([^\n\{]+)', reply)
            if match:
                reply = match.group(1).strip()
            else:
                reply = f"已执行 {fn_name}。"

        if not reply:
            reply = f"已执行 {fn_name}。"

    except Exception as e:
        reply = f"[执行完成，但总结时出错: {e}]"

    return ConfirmResponse(reply=reply, steps=[step])


# ========== 辅助路由 ==========

@router.get("/confirm/pending", response_model=PendingListResponse)
async def list_pending():
    """列出所有待确认的操作"""
    data = _load_pending()
    pending = []
    for cid, ctx in data.items():
        pending.append({
            "confirm_id": cid,
            "type": ctx.get("type", "single_tool"),
            "tool_name": ctx.get("tool_name", "unknown"),
            "goal": ctx.get("goal", ""),
            "created_at": ctx.get("created_at", ""),
        })
    return PendingListResponse(pending=pending, count=len(pending))


@router.delete("/confirm/pending/{cid}")
async def delete_pending(cid: str):
    """删除指定的待确认操作"""
    ctx = pop_confirmation(cid)
    if not ctx:
        raise HTTPException(status_code=404, detail="确认 ID 不存在")
    return {"ok": True, "message": f"已删除待确认操作 {cid}"}


@router.delete("/confirm/pending")
async def clear_pending():
    """清空所有待确认操作"""
    with _pending_lock:
        _save_pending({})
    return {"ok": True, "message": "已清空所有待确认操作"}
