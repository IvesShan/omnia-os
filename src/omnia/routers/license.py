"""
Omnia 授权管理路由 v4.0
======================
在线激活 + 本地验证 + 状态查询 + 更新检测
"""

import json
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ..license import (
    check_license_status,
    verify_license_key,
    save_license,
    activate_trial,
    is_trial_used,
    get_full_status,
    encrypt_api_key,
    decrypt_api_key,
    get_api_key_masked,
    deactivate_license,
    activate_online,
    deactivate_online,
    get_update_info,
    is_online_verified,
    start_background_verifier,
    get_machine_id,
    LICENSE_TYPES,
)

router = APIRouter(prefix="/api/license", tags=["license"])

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/status")
async def get_status() -> JSONResponse:
    """获取授权状态"""
    try:
        is_valid, status_msg, license_data = check_license_status()
        status = get_full_status()

        # 附加在线验证状态
        status["online_verified"] = is_online_verified()

        # 附加更新信息
        update_info = get_update_info()
        if update_info:
            status["update_available"] = update_info

        return JSONResponse(status)
    except Exception as e:
        return JSONResponse({
            "is_valid": False,
            "status": "error",
            "message": f"检查状态失败: {str(e)}",
        }, status_code=500)


@router.post("/activate")
async def activate(request: Request) -> JSONResponse:
    """激活授权（优先在线，离线回退本地验证）"""
    try:
        body = await request.json()
        key = body.get("key", "").strip()
        use_online = body.get("online", True)  # 默认在线激活

        if not key:
            return JSONResponse({"success": False, "message": "请输入卡密"})

        if use_online:
            # 在线激活
            success, message = activate_online(key)
            if success:
                return JSONResponse({"success": True, "message": message, "online": True})

            # 在线失败，尝试本地验证
            is_valid, local_msg, info = verify_license_key(key)
            if is_valid and save_license(info):
                return JSONResponse({
                    "success": True,
                    "message": f"{local_msg}（离线模式）",
                    "online": False,
                    "warning": "离线激活需要在7天内联网验证",
                })

            return JSONResponse({"success": False, "message": message})
        else:
            # 纯本地验证（兼容离线环境）
            is_valid, message, info = verify_license_key(key)
            if is_valid:
                if save_license(info):
                    return JSONResponse({
                        "success": True,
                        "message": message,
                        "online": False,
                    })
                return JSONResponse({"success": False, "message": "许可证保存失败"})
            return JSONResponse({"success": False, "message": message})

    except Exception as e:
        return JSONResponse({"success": False, "message": f"激活失败: {str(e)}"}, status_code=500)


@router.post("/trial")
async def trial() -> JSONResponse:
    """激活试用期"""
    try:
        success, message = activate_trial()
        return JSONResponse({"success": success, "message": message})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"试用激活失败: {str(e)}"}, status_code=500)


@router.post("/deactivate")
async def deactivate(request: Request) -> JSONResponse:
    """停用授权（设备迁移）"""
    try:
        body = await request.json()
        use_online = body.get("online", True)

        if use_online:
            # 获取当前卡密
            from ..license import _load_license_key
            key = _load_license_key()
            if key:
                success, message = deactivate_online(key)
                return JSONResponse({"success": success, "message": message})

        # 离线停用
        success, message = deactivate_license()
        return JSONResponse({"success": success, "message": message})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"停用失败: {str(e)}"}, status_code=500)


@router.get("/api-key")
async def get_api_key() -> JSONResponse:
    """获取脱敏的 API Key"""
    masked = get_api_key_masked()
    has_key = masked is not None
    return JSONResponse({
        "has_key": has_key,
        "masked": masked or "",
    })


@router.post("/api-key")
async def set_api_key(request: Request) -> JSONResponse:
    """设置 API Key"""
    try:
        body = await request.json()
        api_key = body.get("api_key", "").strip()

        if not api_key:
            return JSONResponse({"success": False, "message": "API Key 不能为空"})

        if encrypt_api_key(api_key):
            return JSONResponse({
                "success": True,
                "message": "API Key 已加密保存",
                "masked": get_api_key_masked(),
            })
        return JSONResponse({"success": False, "message": "保存失败"})
    except Exception as e:
        return JSONResponse({"success": False, "message": f"保存失败: {str(e)}"}, status_code=500)


@router.get("/update")
async def check_update() -> JSONResponse:
    """检查更新"""
    update_info = get_update_info()
    if update_info:
        return JSONResponse({
            "has_update": True,
            "update": update_info,
        })
    return JSONResponse({"has_update": False})


@router.get("/types")
async def get_types() -> JSONResponse:
    """获取授权类型列表"""
    return JSONResponse({
        "types": LICENSE_TYPES,
        "machine_id": get_machine_id(),
    })


@router.get("/page", response_class=HTMLResponse)
async def license_page(request: Request) -> HTMLResponse:
    """授权激活页面"""
    return templates.TemplateResponse("license.html", {"request": request})
