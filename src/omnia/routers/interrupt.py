"""Interrupt Manager 路由 - 任务中断管理

支持通过 API 中断正在进行的任务：
- 设置中断标志
- 检查中断状态
- 清除中断
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/interrupt", tags=["Interrupt"])


# ========== 请求/响应模型 ==========

class InterruptRequest(BaseModel):
    """中断请求"""
    reason: str = "user_request"


# ========== 路由端点 ==========

@router.post("/set")
async def set_interrupt(request: InterruptRequest = InterruptRequest()):
    """
    设置中断标志
    
    正在执行的任务会检测到此标志并停止执行。
    """
    try:
        from src.omnia.interrupt_manager import set_interrupt
        
        set_interrupt(request.reason)
        
        return {
            "ok": True,
            "message": "中断标志已设置",
            "reason": request.reason
        }
    except Exception as e:
        logger.error(f"Set interrupt failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_interrupt():
    """清除中断标志"""
    try:
        from src.omnia.interrupt_manager import clear_interrupt
        
        clear_interrupt()
        
        return {
            "ok": True,
            "message": "中断标志已清除"
        }
    except Exception as e:
        logger.error(f"Clear interrupt failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check")
async def check_interrupt():
    """检查是否收到中断信号"""
    try:
        from src.omnia.interrupt_manager import check_interrupt, get_interrupt_info
        
        interrupted = check_interrupt()
        info = get_interrupt_info() if interrupted else None
        
        return {
            "ok": True,
            "interrupted": interrupted,
            "info": info
        }
    except Exception as e:
        logger.error(f"Check interrupt failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_interrupt_info():
    """获取中断详细信息"""
    try:
        from src.omnia.interrupt_manager import get_interrupt_info
        
        info = get_interrupt_info()
        
        if info:
            return {
                "ok": True,
                "interrupted": True,
                "reason": info.get("reason"),
                "timestamp": info.get("timestamp")
            }
        else:
            return {
                "ok": True,
                "interrupted": False,
                "message": "无中断标志"
            }
    except Exception as e:
        logger.error(f"Get interrupt info failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init")
async def init_interrupt_system():
    """初始化中断系统"""
    try:
        from src.omnia.interrupt_manager import init_interrupt_system
        
        init_interrupt_system()
        
        return {
            "ok": True,
            "message": "中断系统已初始化"
        }
    except Exception as e:
        logger.error(f"Init interrupt system failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
