#!/usr/bin/env python3
"""
抖音创作者后台数据获取脚本
使用 Playwright 打开浏览器 → 用户扫码登录 → 自动获取视频数据
"""

import asyncio
import json
import os
import sys
import subprocess
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ 请先安装 playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

# 数据保存路径
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "video_data.json")
PREDICTIONS_FILE = os.path.join(DATA_DIR, "predictions.json")

# 抖音创作者后台 URL
CREATOR_URL = "https://creator.douyin.com/"


async def run():
    print("=" * 60)
    print("🎬 抖音视频数据获取工具")
    print("=" * 60)
    print()
    print("📌 步骤说明：")
    print("  1. 将打开 Chromium 浏览器（可见窗口）")
    print("  2. 请使用抖音扫码登录")
    print("  3. 登录成功后自动获取视频数据")
    print()

    async with async_playwright() as p:
        # 使用系统已安装的 Chrome
        chrome_path = "/usr/bin/google-chrome"
        if not os.path.exists(chrome_path):
            chrome_path = "/usr/bin/chromium-browser"
        
        print(f"  使用浏览器: {chrome_path}")
        
        # 先启动 Chrome 并获取调试端口
        import random
        debug_port = random.randint(9222, 9299)
        
        chrome_proc = subprocess.Popen(
            [
                chrome_path,
                f"--remote-debugging-port={debug_port}",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--user-data-dir=/tmp/omnia_douyin_chrome_profile",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        print(f"  🔗 Chrome 调试端口: {debug_port}")
        print("  ⏳ 等待 Chrome 启动...")
        await asyncio.sleep(3)
        
        # 通过 CDP 连接到已启动的 Chrome
        browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
        print("  ✅ 已连接到 Chrome")
        
        # 获取已有的上下文或创建新的
        contexts = browser.contexts
        if contexts:
            context = contexts[0]
        else:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
        
        # 创建新页面
        page = await context.new_page()
        
        print("🌐 正在打开抖音创作者后台...")
        await page.goto(CREATOR_URL, wait_until="networkidle", timeout=60000)

        # 等待用户扫码登录
        print()
        print("🔐 请在浏览器中扫码登录抖音账号")
        print("⏳ 等待登录...（最多等待 120 秒）")
        print()

        try:
            # 等待跳转到创作者后台（URL 变化表示登录成功）
            await page.wait_for_url(
                "**/creator-home**",
                timeout=120000
            )
            print("✅ 登录成功！")
        except Exception:
            # 也可能跳转到其他页面
            current_url = page.url
            print(f"📍 当前页面: {current_url}")
            if "login" not in current_url.lower():
                print("✅ 似乎已登录成功！")
            else:
                print("❌ 登录超时，请重试")
                await browser.close()
                return

        # 等待页面加载
        await asyncio.sleep(3)

        # 导航到作品管理页面
        print()
        print("📋 正在获取视频数据...")
        print()

        # 尝试多个可能的 URL
        video_urls = [
            "https://creator.douyin.com/creator-micro/content/manage",
            "https://creator.douyin.com/creator-home/content/manage",
        ]

        for url in video_urls:
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                print(f"  已导航到: {url}")
                await asyncio.sleep(2)
                break
            except Exception as e:
                print(f"  ⚠️ 导航失败 {url}: {e}")
                continue

        # 获取页面标题确认
        page_title = await page.title()
        print(f"  页面标题: {page_title}")

        # 滚动加载更多视频
        print("  正在滚动加载视频列表...")
        for i in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            print(f"    滚动 {i+1}/5")

        # ========== 方式1: 从页面 DOM 提取 ==========
        print("\n  📍 方式1: 从页面 DOM 提取...")
        
        # 获取所有视频卡片
        extracted_data = []
        
        # 尝试多种选择器
        selectors = [
            "div[class*='account-item']",
            "div[class*='video-card']",
            "div[class*='content-item']",
            "div[class*='aweme-item']",
            "div[role='listitem']",
            "div[class*='list-item']",
            "div[class*='card-item']",
            "table tbody tr",
        ]
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"    ✅ 选择器 '{selector}' 找到 {len(elements)} 个元素")
                    for el in elements[:10]:
                        try:
                            text = await el.inner_text()
                            extracted_data.append(text[:500])
                        except:
                            pass
            except:
                continue

        # ========== 方式2: 从 API 响应中提取 ==========
        print("\n  📍 方式2: 监听 API 响应...")
        
        api_data = []
        
        async def handle_response(response):
            url = response.url
            if any(x in url for x in ["/aweme/", "/video/", "/post/", "/content/"]):
                try:
                    body = await response.json()
                    api_data.append({
                        "url": url[:200],
                        "status": response.status,
                        "data": str(body)[:2000],
                    })
                except:
                    pass
        
        page.on("response", handle_response)
        
        # 刷新页面以触发 API 请求
        await page.reload(wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5)
        
        print(f"    ✅ 捕获到 {len(api_data)} 个 API 响应")

        # ========== 方式3: 从 JS 变量中提取 ==========
        print("\n  📍 方式3: 从 JS 全局变量提取...")
        
        js_data = None
        try:
            js_data = await page.evaluate("""
                () => {
                    const sources = {};
                    const candidates = ['__NUXT__', '__INITIAL_STATE__', '__NEXT_DATA__', 'window.__DATA__', 'window.__INITIAL_STATE__'];
                    for (const key of candidates) {
                        if (window[key]) {
                            sources[key] = JSON.stringify(window[key]).slice(0, 2000);
                        }
                    }
                    return Object.keys(sources).length > 0 ? sources : null;
                }
            """)
            if js_data:
                print(f"  ✅ 找到全局数据源: {list(js_data.keys())}")
        except Exception as e:
            print(f"  ⚠️ JS 变量提取失败: {e}")

        # ========== 保存页面 HTML 用于调试 ==========
        page_html = await page.content()
        html_path = os.path.join(DATA_DIR, "page_debug.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page_html)
        print(f"\n  💾 页面 HTML 已保存 (大小: {len(page_html)} 字符)")

        # ========== 整理结果 ==========
        result = {
            "account": "抖音账号",
            "fetch_time": datetime.now().isoformat(),
            "source": "抖音创作者后台",
            "page_url": page.url,
            "page_title": page_title,
            "videos_dom_count": len(extracted_data),
            "api_responses_count": len(api_data),
            "js_data_sources": list(js_data.keys()) if js_data else [],
            "videos": extracted_data,
            "api_responses": api_data[:5] if api_data else [],
            "js_data": js_data,
        }

        # 保存数据
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n  💾 数据已保存到: {OUTPUT_FILE}")
        print(f"  📊 DOM 提取: {len(extracted_data)} 条")
        print(f"  📊 API 捕获: {len(api_data)} 条")
        print(f"  📊 JS 数据源: {list(js_data.keys()) if js_data else '无'}")

        # 尝试从 API 数据中提取结构化视频统计
        if api_data:
            try:
                structured = extract_video_stats(api_data)
                if structured and structured.get("videos"):
                    with open(PREDICTIONS_FILE, "w", encoding="utf-8") as f:
                        json.dump(structured, f, ensure_ascii=False, indent=2)
                    print(f"  📈 预测数据已保存到: {PREDICTIONS_FILE} ({len(structured['videos'])} 条)")
            except Exception as e:
                print(f"  ⚠️ 结构化提取失败: {e}")

        print()
        print("=" * 60)
        print("✅ 数据获取完成！")
        print("=" * 60)
        print()
        print("💡 浏览器保持打开，你可以查看数据")
        print("   关闭浏览器窗口即可退出...")

        # 保持浏览器打开
        while True:
            try:
                if not page.is_closed():
                    await asyncio.sleep(1)
                else:
                    break
            except:
                break


def extract_video_stats(api_data):
    """从 API 响应中提取视频统计数据"""
    videos = []
    
    for item in api_data:
        data_str = item.get("data", "")
        try:
            # 尝试解析 JSON
            if isinstance(data_str, str):
                data = json.loads(data_str)
            else:
                data = data_str
            
            # 递归查找视频列表
            def find_videos(obj, depth=0):
                if depth > 5:
                    return
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key in ["aweme_list", "video_list", "list", "data", "items"] and isinstance(value, list):
                            for v in value:
                                if isinstance(v, dict):
                                    videos.append(v)
                        else:
                            find_videos(value, depth + 1)
                elif isinstance(obj, list):
                    for item in obj:
                        find_videos(item, depth + 1)
            
            find_videos(data)
        except:
            pass
    
    return {"videos": videos, "count": len(videos)} if videos else None


if __name__ == "__main__":
    asyncio.run(run())
