"""Computer Controller 路由 - 电脑控制

让 Omnia 能够像真人一样操作电脑：
- 屏幕截图
- 鼠标操作
- 键盘输入
- 屏幕分析
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import base64

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/computer", tags=["Computer"])


# ========== 请求/响应模型 ==========

class ScreenshotRequest(BaseModel):
    """截图请求"""
    save_path: Optional[str] = None


class MouseMoveRequest(BaseModel):
    """鼠标移动请求"""
    x: int
    y: int
    duration: float = 0.5


class MouseClickRequest(BaseModel):
    """鼠标点击请求"""
    x: Optional[int] = None
    y: Optional[int] = None
    button: str = "left"  # left, right, middle
    clicks: int = 1


class KeyboardTypeRequest(BaseModel):
    """键盘输入请求"""
    text: str
    interval: float = 0.05


class KeyboardKeyRequest(BaseModel):
    """键盘按键请求"""
    key: str  # enter, tab, escape, etc.
    presses: int = 1


class AnalyzeRequest(BaseModel):
    """屏幕分析请求"""
    instruction: str = "描述屏幕内容，列出所有可操作的元素"


class ExecuteRequest(BaseModel):
    """执行操作请求"""
    command: str  # 自然语言命令


# ========== 路由端点 ==========

@router.get("/status")
async def get_status():
    """获取电脑控制器状态"""
    try:
        import pyautogui
        width, height = pyautogui.size()
        x, y = pyautogui.position()
        
        return {
            "ok": True,
            "available": True,
            "screen": {
                "width": width,
                "height": height
            },
            "mouse_position": {"x": x, "y": y},
            "safety_mode": pyautogui.FAILSAFE
        }
    except ImportError:
        return {
            "ok": True,
            "available": False,
            "message": "pyautogui 未安装，运行: pip install pyautogui pillow"
        }
    except Exception as e:
        return {
            "ok": True,
            "available": False,
            "error": str(e)
        }


@router.post("/screenshot")
async def take_screenshot(request: ScreenshotRequest = ScreenshotRequest()):
    """截取屏幕"""
    try:
        from src.omnia.computer_controller import OmniaController
        import io
        
        controller = OmniaController()
        img = controller.screenshot(request.save_path)
        
        # 转换为 base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "ok": True,
            "image": img_base64,
            "size": {"width": img.width, "height": img.height},
            "saved_to": request.save_path
        }
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_screen(request: AnalyzeRequest):
    """分析屏幕内容"""
    try:
        from src.omnia.computer_controller import OmniaController
        
        controller = OmniaController()
        result = controller.analyze_screen(request.instruction)
        
        return {
            "ok": True,
            "analysis": result
        }
    except Exception as e:
        logger.error(f"Screen analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mouse/move")
async def move_mouse(request: MouseMoveRequest):
    """移动鼠标"""
    try:
        import pyautogui
        
        pyautogui.moveTo(request.x, request.y, duration=request.duration)
        
        return {
            "ok": True,
            "message": f"鼠标已移动到 ({request.x}, {request.y})",
            "position": {"x": request.x, "y": request.y}
        }
    except Exception as e:
        logger.error(f"Mouse move failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mouse/click")
async def click_mouse(request: MouseClickRequest):
    """点击鼠标"""
    try:
        import pyautogui
        
        if request.x is not None and request.y is not None:
            pyautogui.click(request.x, request.y, clicks=request.clicks, button=request.button)
        else:
            pyautogui.click(clicks=request.clicks, button=request.button)
        
        return {
            "ok": True,
            "message": f"鼠标 {request.button} 键点击 {request.clicks} 次"
        }
    except Exception as e:
        logger.error(f"Mouse click failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mouse/scroll")
async def scroll_mouse(direction: str = "up", amount: int = 3):
    """滚动鼠标"""
    try:
        import pyautogui
        
        if direction == "up":
            pyautogui.scroll(amount)
        else:
            pyautogui.scroll(-amount)
        
        return {
            "ok": True,
            "message": f"鼠标向{direction}滚动 {amount} 单位"
        }
    except Exception as e:
        logger.error(f"Mouse scroll failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keyboard/type")
async def type_text(request: KeyboardTypeRequest):
    """输入文本"""
    try:
        import pyautogui
        
        pyautogui.typewrite(request.text, interval=request.interval)
        
        return {
            "ok": True,
            "message": f"已输入 {len(request.text)} 个字符"
        }
    except Exception as e:
        logger.error(f"Keyboard type failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keyboard/press")
async def press_key(request: KeyboardKeyRequest):
    """按下按键"""
    try:
        import pyautogui
        
        pyautogui.press(request.key, presses=request.presses)
        
        return {
            "ok": True,
            "message": f"已按下 {request.key} 键 {request.presses} 次"
        }
    except Exception as e:
        logger.error(f"Key press failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keyboard/hotkey")
async def press_hotkey(keys: List[str]):
    """按下组合键"""
    try:
        import pyautogui
        
        pyautogui.hotkey(*keys)
        
        return {
            "ok": True,
            "message": f"已按下组合键: {'+'.join(keys)}"
        }
    except Exception as e:
        logger.error(f"Hotkey failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_command(request: ExecuteRequest):
    """
    执行自然语言命令
    
    例如：
    - "打开浏览器，搜索今天的新闻"
    - "截图并分析屏幕内容"
    - "点击确定按钮"
    """
    try:
        from src.omnia.computer_controller import OmniaController
        
        controller = OmniaController()
        result = controller.execute(request.command)
        
        return {
            "ok": True,
            "command": request.command,
            "result": result
        }
    except Exception as e:
        logger.error(f"Execute command failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emergency-stop")
async def emergency_stop():
    """紧急停止 - 将鼠标移动到屏幕角落"""
    try:
        import pyautogui
        
        # 移动到左上角触发 FAILSAFE
        pyautogui.moveTo(0, 0)
        
        return {
            "ok": True,
            "message": "紧急停止已触发"
        }
    except Exception as e:
        # FAILSAFE 触发时会抛出异常，这是正常的
        return {
            "ok": True,
            "message": "紧急停止成功（FAILSAFE 触发）"
        }
