"""
Omnia 授权管理路由
版本：v2 - 使用异步函数，避免阻塞
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Dict, Any

from ..license import check_license_status, activate_license, get_license_display

router = APIRouter(prefix="/api/license", tags=["license"])

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/status")
async def get_status() -> JSONResponse:
    """获取授权状态"""
    try:
        is_valid, status, license_data = await check_license_status()
        
        if license_data is None:
            return JSONResponse({
                "is_valid": False,
                "status": "inactive",
                "message": status,
            })
        
        if not is_valid:
            if status == "已过期":
                return JSONResponse({
                    "is_valid": False,
                    "status": "expired",
                    "message": status,
                    "expire_time": license_data.get("expire_time"),
                    "type_label": license_data.get("type_label"),
                })
            return JSONResponse({
                "is_valid": False,
                "status": "inactive",
                "message": status,
            })
        
        from datetime import datetime
        try:
            expire_time = datetime.strptime(license_data["expire_time"], "%Y-%m-%d %H:%M:%S")
            remaining_days = (expire_time - datetime.now()).days
        except:
            remaining_days = 0
        
        return JSONResponse({
            "is_valid": True,
            "status": "active",
            "message": status,
            "type": license_data.get("type"),
            "type_label": license_data.get("type_label"),
            "activate_time": license_data.get("activate_time"),
            "expire_time": license_data.get("expire_time"),
            "remaining_days": remaining_days,
        })
    except Exception as e:
        return JSONResponse({
            "is_valid": False,
            "status": "error",
            "message": f"检查状态失败: {str(e)}",
        }, status_code=500)


@router.post("/activate")
async def activate(request: Request) -> JSONResponse:
    """激活授权"""
    try:
        body = await request.json()
        key = body.get("key", "").strip()
        
        if not key:
            return JSONResponse({
                "success": False,
                "message": "请输入卡密",
            })
        
        success, message = await activate_license(key)
        
        return JSONResponse({
            "success": success,
            "message": message,
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "message": f"激活失败: {str(e)}",
        }, status_code=500)


@router.get("/display")
async def display() -> JSONResponse:
    """获取授权显示信息"""
    try:
        display_text = await get_license_display()
        return JSONResponse({"display": display_text})
    except Exception as e:
        return JSONResponse({
            "display": f"❌ 获取失败: {str(e)}",
        }, status_code=500)


@router.get("/page", response_class=HTMLResponse)
async def license_page(request: Request) -> HTMLResponse:
    """授权激活页面"""
    return templates.TemplateResponse("license.html", {"request": request})
