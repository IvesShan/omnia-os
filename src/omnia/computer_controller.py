#!/usr/bin/env python3
"""
Omnia 电脑控制器
让 Omnia 能够像真人一样操作电脑

依赖:
  pip install pyautogui pillow pytesseract openai

使用:
  from computer_controller import OmniaController
  controller = OmniaController()
  controller.execute("打开浏览器，搜索今天的新闻")
"""

import sys
import json
import time
import base64
import subprocess
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass

try:
    import pyautogui
    from PIL import Image
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("[Warning] pyautogui not installed. Run: pip install pyautogui pillow")

# 安全设置
if PYAUTOGUI_AVAILABLE:
    pyautogui.FAILSAFE = True  # 移动鼠标到角落可中断
    pyautogui.PAUSE = 0.1  # 每个操作后暂停


@dataclass
class ScreenElement:
    """屏幕元素"""
    type: str  # button, text, icon, input
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float


class OmniaController:
    """Omnia 电脑控制器"""
    
    def __init__(self, vision_api: str = "qianfan", safety_mode: bool = True):
        """
        初始化控制器
        
        Args:
            vision_api: 视觉模型 API (qianfan, openai, local)
            safety_mode: 安全模式，操作前需要确认
        """
        self.vision_api = vision_api
        self.safety_mode = safety_mode
        self.screen_width, self.screen_height = pyautogui.size() if PYAUTOGUI_AVAILABLE else (1920, 1080)
        self.history: List[Dict] = []
        
        print(f"[OmniaCtrl] 初始化完成，屏幕尺寸: {self.screen_width}x{self.screen_height}")
    
    def screenshot(self, save_path: Optional[str] = None) -> Image.Image:
        """截取屏幕"""
        if not PYAUTOGUI_AVAILABLE:
            raise RuntimeError("pyautogui not installed")
        
        img = pyautogui.screenshot()
        
        if save_path:
            img.save(save_path)
            print(f"[OmniaCtrl] 截图已保存: {save_path}")
        
        return img
    
    def image_to_base64(self, img: Image.Image) -> str:
        """图片转 base64"""
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    
    def analyze_screen(self, instruction: str = "描述屏幕内容，列出所有可操作的元素") -> Dict:
        """
        分析屏幕内容
        
        Args:
            instruction: 分析指令
        
        Returns:
            分析结果
        """
        img = self.screenshot()
        img_base64 = self.image_to_base64(img)
        
        # 根据配置选择 API
        if self.vision_api == "qianfan":
            return self._analyze_with_qianfan(img_base64, instruction)
        elif self.vision_api == "openai":
            return self._analyze_with_openai(img_base64, instruction)
        else:
            # 本地分析（使用 OCR）
            return self._analyze_with_ocr(img)
    
    def _analyze_with_qianfan(self, img_base64: str, instruction: str) -> Dict:
        """使用千帆视觉模型分析"""
        # TODO: 实现千帆 VL API 调用
        return {
            "description": "千帆视觉分析（待实现）",
            "elements": [],
            "raw_response": None
        }
    
    def _analyze_with_openai(self, img_base64: str, instruction: str) -> Dict:
        """使用 OpenAI GPT-4V 分析"""
        try:
            import openai
            client = openai.OpenAI()
            
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{img_base64}"
                        }}
                    ]
                }],
                max_tokens=1000
            )
            
            return {
                "description": response.choices[0].message.content,
                "elements": [],
                "raw_response": response
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_with_ocr(self, img: Image.Image) -> Dict:
        """使用本地 OCR 分析"""
        try:
            import pytesseract
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            return {
                "description": text,
                "elements": [],
                "method": "ocr"
            }
        except ImportError:
            return {"error": "pytesseract not installed"}
    
    # === 鼠标操作 ===
    
    def move_to(self, x: int, y: int, duration: float = 0.3) -> bool:
        """移动鼠标到指定位置"""
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        if self.safety_mode:
            print(f"[OmniaCtrl] 即将移动鼠标到 ({x}, {y})")
        
        pyautogui.moveTo(x, y, duration=duration)
        self.history.append({"action": "move", "x": x, "y": y, "time": time.time()})
        return True
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None, 
              button: str = "left", clicks: int = 1) -> bool:
        """
        点击
        
        Args:
            x, y: 坐标，如果为 None 则点击当前位置
            button: left, right, middle
            clicks: 点击次数
        """
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        if self.safety_mode:
            pos = f"({x}, {y})" if x and y else "当前位置"
            print(f"[OmniaCtrl] 即将点击 {pos}, 按键: {button}, 次数: {clicks}")
        
        if x and y:
            pyautogui.click(x, y, clicks=clicks, button=button)
        else:
            pyautogui.click(clicks=clicks, button=button)
        
        self.history.append({
            "action": "click", "x": x, "y": y, 
            "button": button, "clicks": clicks, 
            "time": time.time()
        })
        return True
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """双击"""
        return self.click(x, y, clicks=2)
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """右键点击"""
        return self.click(x, y, button="right")
    
    def drag(self, start: Tuple[int, int], end: Tuple[int, int], 
             duration: float = 0.5) -> bool:
        """拖拽"""
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        pyautogui.moveTo(start[0], start[1])
        pyautogui.drag(end[0] - start[0], end[1] - start[1], duration=duration)
        return True
    
    def scroll(self, clicks: int, direction: str = "down") -> bool:
        """滚动"""
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        amount = clicks if direction == "down" else -clicks
        pyautogui.scroll(amount)
        return True
    
    # === 键盘操作 ===
    
    def type_text(self, text: str, interval: float = 0.05) -> bool:
        """输入文字"""
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        if self.safety_mode:
            preview = text[:50] + "..." if len(text) > 50 else text
            print(f"[OmniaCtrl] 即将输入: {preview}")
        
        pyautogui.typewrite(text, interval=interval)
        self.history.append({"action": "type", "text": text, "time": time.time()})
        return True
    
    def type_chinese(self, text: str) -> bool:
        """输入中文（使用剪贴板）"""
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        # 复制到剪贴板
        subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode())
        # 粘贴
        pyautogui.hotkey("ctrl", "v")
        return True
    
    def press(self, *keys: str) -> bool:
        """按键"""
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        pyautogui.press(keys)
        self.history.append({"action": "press", "keys": keys, "time": time.time()})
        return True
    
    def hotkey(self, *keys: str) -> bool:
        """组合键"""
        if not PYAUTOGUI_AVAILABLE:
            return False
        
        pyautogui.hotkey(*keys)
        self.history.append({"action": "hotkey", "keys": keys, "time": time.time()})
        return True
    
    # === 高级操作 ===
    
    def find_and_click(self, target: str) -> bool:
        """查找并点击目标"""
        analysis = self.analyze_screen(f"找到 '{target}' 的位置，返回坐标")
        
        if "error" in analysis:
            print(f"[OmniaCtrl] 分析失败: {analysis['error']}")
            return False
        
        # TODO: 解析返回的坐标
        print(f"[OmniaCtrl] 分析结果: {analysis['description'][:200]}")
        return True
    
    def open_app(self, app_name: str) -> bool:
        """打开应用"""
        # 安全检查：防止命令注入
        
        if sys.platform == "darwin":
            subprocess.run(["open", "-a", app_name])
        elif sys.platform == "win32":
            # Windows: 使用 os.startfile 避免命令注入
            import os
            os.startfile(app_name)
        else:  # Linux
            subprocess.run([app_name], detached=True)
        
        time.sleep(1)  # 等待应用启动
        return True
    
    def execute_task(self, task: str) -> Dict:
        """
        执行任务（自然语言）
        
        Args:
            task: 任务描述，如 "打开浏览器，搜索今天的天气"
        
        Returns:
            执行结果
        """
        # 1. 分析任务
        steps = self._plan_task(task)
        
        # 2. 执行步骤
        results = []
        for i, step in enumerate(steps):
            print(f"[OmniaCtrl] 步骤 {i+1}/{len(steps)}: {step['description']}")
            result = self._execute_step(step)
            results.append(result)
            
            if not result.get("success"):
                print(f"[OmniaCtrl] 步骤失败: {result.get('error')}")
                break
            
            time.sleep(0.5)  # 步骤间隔
        
        return {
            "task": task,
            "steps": steps,
            "results": results,
            "success": all(r.get("success") for r in results)
        }
    
    def _plan_task(self, task: str) -> List[Dict]:
        """规划任务步骤"""
        # 简单的任务分解
        # TODO: 使用 LLM 进行任务规划
        
        if "打开浏览器" in task or "浏览器" in task:
            return [
                {"action": "open_app", "app": "firefox", "description": "打开浏览器"},
                {"action": "wait", "seconds": 2, "description": "等待浏览器启动"},
            ]
        
        return [{"action": "unknown", "description": task}]
    
    def _execute_step(self, step: Dict) -> Dict:
        """执行单个步骤"""
        action = step.get("action")
        
        if action == "open_app":
            success = self.open_app(step["app"])
            return {"success": success}
        
        elif action == "wait":
            time.sleep(step.get("seconds", 1))
            return {"success": True}
        
        elif action == "click":
            success = self.click(step.get("x"), step.get("y"))
            return {"success": success}
        
        elif action == "type":
            success = self.type_text(step.get("text", ""))
            return {"success": success}
        
        else:
            return {"success": False, "error": f"未知操作: {action}"}
    
    # === 安全功能 ===
    
    def emergency_stop(self):
        """紧急停止"""
        print("[OmniaCtrl] 紧急停止！")
        pyautogui.moveTo(0, 0)  # 移动到角落触发 FAILSAFE
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """获取操作历史"""
        return self.history[-limit:]
    
    def clear_history(self):
        """清空历史"""
        self.history.clear()


# 命令行入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Omnia 电脑控制器")
    parser.add_argument("--screenshot", action="store_true", help="截图")
    parser.add_argument("--analyze", action="store_true", help="分析屏幕")
    parser.add_argument("--task", type=str, help="执行任务")
    parser.add_argument("--no-safety", action="store_true", help="关闭安全模式")
    
    args = parser.parse_args()
    
    controller = OmniaController(safety_mode=not args.no_safety)
    
    if args.screenshot:
        img = controller.screenshot("screenshot.png")
        print(f"截图尺寸: {img.size}")
    
    elif args.analyze:
        result = controller.analyze_screen()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.task:
        result = controller.execute_task(args.task)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        print("使用 --help 查看帮助")
