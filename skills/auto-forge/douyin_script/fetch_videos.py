#!/usr/bin/env python3
"""抖音视频数据获取脚本 - 使用已登录的Chrome实例"""

import asyncio
import json
import os
import sys
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "videos_data.json")
os.makedirs(DATA_DIR, exist_ok=True)

DEBUG_DIR = "/tmp/omnia_douyin"
os.makedirs(DEBUG_DIR, exist_ok=True)


async def fetch_videos():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        print("🔗 连接到已启动的 Chrome...")
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9267")
        print("✅ 已连接到 Chrome")

        # 使用已有上下文
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()

        # 导航到作品管理
        print("🌐 正在打开作品管理页面...")
        await page.goto(
            "https://creator.douyin.com/creator-micro/content/manage",
            wait_until="networkidle",
            timeout=30000,
        )
        await asyncio.sleep(3)
        print(f"📍 当前URL: {page.url}")

        # 保存页面截图
        await page.screenshot(path=os.path.join(DEBUG_DIR, "content_page.png"))
        print("📸 页面截图已保存")

        # 滚动加载更多视频
        print("📜 正在滚动加载视频列表...")
        for i in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            print(f"   滚动 {i+1}/5")

        # 保存页面HTML
        html = await page.content()
        with open(os.path.join(DEBUG_DIR, "page_content.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"💾 HTML已保存 ({len(html)} 字符)")

        # 尝试多种方式提取视频数据
        all_videos = []

        # 方式1: 从页面DOM提取
        print("\n🔍 方式1: 从页面DOM提取...")
        dom_data = await page.evaluate("""
            () => {
                const videos = [];
                // 尝试查找视频列表中的元素
                const elements = document.querySelectorAll('*');
                for (const el of elements) {
                    const text = el.textContent.trim();
                    if (text.includes('播放') && text.includes('点赞') && text.length < 500) {
                        videos.push(text.substring(0, 300));
                    }
                }
                return videos.slice(0, 100);
            }
        """)
        print(f"   找到 {len(dom_data)} 个包含播放/点赞的文本片段")
        for item in dom_data[:5]:
            print(f"   - {item[:100]}")

        # 方式2: 从JS全局变量提取
        print("\n🔍 方式2: 从JS全局变量提取...")
        js_data = await page.evaluate("""
            () => {
                const sources = {};
                const candidates = [
                    '__NUXT__', '__INITIAL_STATE__', '__NEXT_DATA__',
                    'window.__DATA__', 'window.__INITIAL_STATE__',
                    '__NEXT_DATA__', '__RENDER_DATA__'
                ];
                for (const key of candidates) {
                    try {
                        if (window[key]) {
                            sources[key] = typeof window[key] === 'object' 
                                ? JSON.stringify(window[key]).substring(0, 5000)
                                : String(window[key]).substring(0, 5000);
                        }
                    } catch(e) {}
                }
                return sources;
            }
        """)
        if js_data:
            print(f"   找到全局数据源: {list(js_data.keys())}")
        else:
            print("   ⚠️ 未找到全局数据源")

        # 方式3: 从页面文本中提取结构化数据
        print("\n🔍 方式3: 提取页面中的结构化数据...")
        page_text = await page.evaluate("() => document.body.innerText")
        lines = [l.strip() for l in page_text.split('\n') if l.strip()]
        
        # 查找视频相关的行
        video_lines = []
        for i, line in enumerate(lines):
            if any(kw in line for kw in ['播放', '点赞', '评论', '分享', '发布时间']):
                context_lines = lines[max(0,i-2):i+3]
                video_lines.append(' | '.join(context_lines))
        
        print(f"   找到 {len(video_lines)} 个视频数据片段")
        for vl in video_lines[:10]:
            print(f"   📹 {vl[:150]}")

        # 方式4: 监控网络请求
        print("\n🔍 方式4: 监控API请求...")
        api_calls = []
        
        async def on_response(response):
            url = response.url
            if any(x in url for x in ['/aweme/', '/video/', '/post/', '/content/', '/manage/']):
                try:
                    body = await response.json()
                    api_calls.append({
                        'url': url[:200],
                        'status': response.status,
                        'data_preview': json.dumps(body, ensure_ascii=False)[:2000]
                    })
                except:
                    api_calls.append({
                        'url': url[:200],
                        'status': response.status,
                        'data_preview': None
                    })
        
        page.on('response', on_response)
        
        # 刷新页面
        print("   正在刷新页面以捕获API请求...")
        await page.reload(wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        print(f"   捕获到 {len(api_calls)} 个API响应")
        for api in api_calls[:15]:
            print(f"   [{api['status']}] {api['url'][:100]}")

        # 整理结果
        result = {
            "account": "抖音账号",
            "fetch_time": datetime.now().isoformat(),
            "source": "抖音创作者后台",
            "page_url": page.url,
            "dom_extracted_count": len(dom_data),
            "api_responses_count": len(api_calls),
            "js_data_sources": list(js_data.keys()) if js_data else [],
            "video_text_lines": video_lines[:50],
            "dom_samples": dom_data[:20],
            "api_responses": api_calls[:20],
            "js_data": js_data,
        }

        # 保存数据
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 数据已保存到: {OUTPUT_FILE}")

        # 保存API数据到单独文件
        if api_calls:
            api_file = os.path.join(DATA_DIR, "api_responses.json")
            with open(api_file, "w", encoding="utf-8") as f:
                json.dump(api_calls, f, ensure_ascii=False, indent=2)
            print(f"✅ API响应已保存到: {api_file}")

        print("\n✅ 完成！")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(fetch_videos())
