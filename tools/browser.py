#!/usr/bin/env python3
"""
Omnia 浏览器工具 - 基于 DrissionPage
支持：
  - 打开网页
  - 扫码登录（保持会话）
  - 抓取页面数据
  - 截图
  - 元素交互

用法：
  python3 tools/browser.py open URL          # 打开网页并截图
  python3 tools/browser.py login URL         # 打开网页等待扫码登录
  python3 tools/browser.py screenshot        # 当前页面截图
  python3 tools/browser.py text              # 获取页面文本
  python3 tools/browser.py html              # 获取页面HTML
  python3 tools/browser.py click TEXT        # 点击包含文本的元素
  python3 tools/browser.py type TEXT VALUE   # 在输入框输入文字
  python3 tools/browser.py close             # 关闭浏览器
"""

import sys
import json
import os
import time
from DrissionPage import ChromiumPage, ChromiumOptions

# 会话数据目录
SESSION_DIR = os.path.expanduser("~/.openclaw/workspace/omnia-os/.omnia/browser_session")
SCREENSHOT_DIR = os.path.expanduser("~/.openclaw/workspace/omnia-os/.omnia/screenshots")

os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 全局浏览器实例
_page = None


def get_browser(headless=False):
    """获取或创建浏览器实例"""
    global _page
    if _page is not None:
        try:
            _page.url  # 测试连接是否有效
            return _page
        except:
            _page = None
    
    co = ChromiumOptions()
    co.set_user_data_path(SESSION_DIR)
    co.set_browser_path('/usr/bin/google-chrome')
    co.auto_port()
    
    if headless:
        co.headless()
    
    # 添加保持登录的配置
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--disable-infobars')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    
    _page = ChromiumPage(co)
    return _page


def save_screenshot(page, name="screenshot"):
    """保存截图"""
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    page.get_screenshot(path=path, full_page=False)
    return path


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    try:
        if action == "open":
            url = sys.argv[2] if len(sys.argv) > 2 else "https://www.douyin.com"
            page = get_browser()
            page.get(url)
            page.wait.load_start()
            time.sleep(3)
            screenshot_path = save_screenshot(page, "page_open")
            print(json.dumps({
                "status": "ok",
                "url": page.url,
                "title": page.title,
                "screenshot": screenshot_path
            }, ensure_ascii=False))
        
        elif action == "login":
            url = sys.argv[2] if len(sys.argv) > 2 else "https://creator.douyin.com"
            page = get_browser()
            page.get(url)
            page.wait.load_start()
            time.sleep(5)
            screenshot_path = save_screenshot(page, "login_page")
            
            # 检查是否已登录
            if "login" not in page.url.lower() and "creator.douyin.com" in page.url:
                print(json.dumps({
                    "status": "already_logged_in",
                    "message": "已登录，无需扫码",
                    "url": page.url,
                    "screenshot": screenshot_path
                }, ensure_ascii=False))
            else:
                print(json.dumps({
                    "status": "waiting_scan",
                    "message": "请扫码登录，登录完成后运行: python3 tools/browser.py data",
                    "url": page.url,
                    "screenshot": screenshot_path
                }, ensure_ascii=False))
                print("\n⏳ 浏览器已打开，等待扫码登录...")
                print("登录完成后按 Ctrl+C 关闭此脚本（浏览器会保持打开）")
                try:
                    while True:
                        time.sleep(2)
                        current_url = page.url
                        if "creator.douyin.com" in current_url and "login" not in current_url.lower():
                            screenshot_path = save_screenshot(page, "login_success")
                            print(f"\n✅ 登录成功！当前页面: {current_url}")
                            print(f"📸 截图: {screenshot_path}")
                            break
                except KeyboardInterrupt:
                    print("\n⚠️ 手动中断，浏览器保持打开状态")
        
        elif action == "screenshot":
            page = get_browser()
            name = sys.argv[2] if len(sys.argv) > 2 else "screenshot"
            screenshot_path = save_screenshot(page, name)
            print(json.dumps({
                "status": "ok",
                "screenshot": screenshot_path,
                "url": page.url,
                "title": page.title
            }, ensure_ascii=False))
        
        elif action == "text":
            page = get_browser()
            try:
                text = page.ele('tag:body').text
            except:
                text = page.html.text if hasattr(page.html, 'text') else str(page.html)[:5000]
            print(json.dumps({
                "status": "ok",
                "url": page.url,
                "title": page.title,
                "text": text[:8000]
            }, ensure_ascii=False))
        
        elif action == "html":
            page = get_browser()
            print(json.dumps({
                "status": "ok",
                "url": page.url,
                "title": page.title,
                "html": str(page.html)[:15000]
            }, ensure_ascii=False))
        
        elif action == "data":
            # 抖音创作者后台数据抓取
            page = get_browser()
            
            # 先访问主页确认登录状态
            page.get("https://creator.douyin.com/creator-micro/home")
            time.sleep(3)
            
            if "login" in page.url.lower():
                print(json.dumps({
                    "status": "need_login",
                    "message": "会话已过期，请重新登录",
                    "url": page.url
                }, ensure_ascii=False))
                return
            
            # 访问数据页面
            page.get("https://creator.douyin.com/creator-micro/data/manage")
            time.sleep(5)
            screenshot_path = save_screenshot(page, "douyin_data")
            
            # 获取页面文本
            try:
                text = page.ele('tag:body').text
            except:
                text = "无法获取文本"
            
            print(json.dumps({
                "status": "ok",
                "url": page.url,
                "screenshot": screenshot_path,
                "text": text[:10000]
            }, ensure_ascii=False))
        
        elif action == "videos":
            # 获取视频列表
            page = get_browser()
            
            # 访问作品管理页面
            page.get("https://creator.douyin.com/creator-micro/content/manage")
            time.sleep(5)
            screenshot_path = save_screenshot(page, "douyin_videos")
            
            # 获取页面文本
            try:
                text = page.ele('tag:body').text
            except:
                text = "无法获取文本"
            
            print(json.dumps({
                "status": "ok",
                "url": page.url,
                "screenshot": screenshot_path,
                "text": text[:15000]
            }, ensure_ascii=False))
        
        elif action == "click":
            # 点击元素
            text = sys.argv[2] if len(sys.argv) > 2 else ""
            page = get_browser()
            try:
                element = page.ele(f'text:{text}')
                element.click()
                time.sleep(2)
                screenshot_path = save_screenshot(page, "after_click")
                print(json.dumps({
                    "status": "ok",
                    "clicked": text,
                    "screenshot": screenshot_path,
                    "url": page.url
                }, ensure_ascii=False))
            except Exception as e:
                print(json.dumps({
                    "status": "error",
                    "error": f"未找到元素: {text}",
                    "details": str(e)
                }, ensure_ascii=False))
        
        elif action == "type":
            # 输入文字
            selector = sys.argv[2] if len(sys.argv) > 2 else ""
            value = sys.argv[3] if len(sys.argv) > 3 else ""
            page = get_browser()
            try:
                element = page.ele(selector)
                element.clear()
                element.input(value)
                time.sleep(1)
                print(json.dumps({
                    "status": "ok",
                    "typed": value,
                    "selector": selector
                }, ensure_ascii=False))
            except Exception as e:
                print(json.dumps({
                    "status": "error",
                    "error": f"输入失败",
                    "details": str(e)
                }, ensure_ascii=False))
        
        elif action == "close":
            global _page
            if _page:
                _page.quit()
                _page = None
            print(json.dumps({"status": "ok", "message": "浏览器已关闭"}, ensure_ascii=False))
        
        elif action == "status":
            # 检查浏览器状态
            try:
                page = get_browser()
                print(json.dumps({
                    "status": "ok",
                    "url": page.url,
                    "title": page.title,
                    "is_logged_in": "login" not in page.url.lower()
                }, ensure_ascii=False))
            except Exception as e:
                print(json.dumps({
                    "status": "error",
                    "error": str(e)
                }, ensure_ascii=False))
        
        else:
            print(f"未知操作: {action}")
            print(__doc__)
            sys.exit(1)
    
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
