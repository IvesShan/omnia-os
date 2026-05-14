#!/usr/bin/env python3
"""从抖音创作者后台提取视频数据"""

import asyncio
import json
import os
import re
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


async def extract_videos():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9267")
        context = browser.contexts[0]
        page = await context.new_page()

        # 导航到作品管理
        print("🌐 正在打开作品管理页面...")
        await page.goto(
            "https://creator.douyin.com/creator-micro/content/manage",
            wait_until="networkidle",
            timeout=30000,
        )
        await asyncio.sleep(3)
        print(f"📍 {page.url}")

        # 滚动加载
        print("📜 滚动加载视频列表...")
        for i in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            print(f"   滚动 {i+1}/5")

        # 获取页面文本
        page_text = await page.evaluate("() => document.body.innerText")
        lines = [l.strip() for l in page_text.split("\n") if l.strip()]

        print(f"📄 页面文本行数: {len(lines)}")

        # 提取视频数据块
        # 抖音创作者后台的典型结构：
        # [标题行]
        # 202X年XX月XX日 XX:XX | 已发布
        # 播放 XX 点赞 XX 评论 XX 分享 XX

        video_blocks = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # 找到包含播放数据的行
            if re.match(r"^播放\s+", line):
                # 回溯找标题
                block_start = max(0, i - 5)
                block = lines[block_start : i + 1]
                video_blocks.append(block)
            i += 1

        print(f"🔍 找到 {len(video_blocks)} 个视频数据块")

        # 解析每个视频块
        parsed_videos = []
        for block in video_blocks:
            video = {"title": "", "playCount": "", "diggCount": "", "commentCount": "", "shareCount": "", "publishTime": ""}

            for line in block:
                # 提取标题（非统计行、非时间行）
                if not re.match(r"^(播放|点赞|评论|分享|\d{4}年)", line) and len(line) > 5:
                    if not video["title"]:
                        video["title"] = line[:100]

                # 提取发布时间
                time_match = re.search(r"(\d{4}年\d{2}月\d{2}日\s*\d{2}:\d{2})", line)
                if time_match:
                    video["publishTime"] = time_match.group(1)

                # 提取统计数据
                parts = line.split()
                for j, part in enumerate(parts):
                    if part == "播放" and j + 1 < len(parts):
                        video["playCount"] = parts[j + 1]
                    elif part == "点赞" and j + 1 < len(parts):
                        video["diggCount"] = parts[j + 1]
                    elif part == "评论" and j + 1 < len(parts):
                        video["commentCount"] = parts[j + 1]
                    elif part == "分享" and j + 1 < len(parts):
                        video["shareCount"] = parts[j + 1]

            if video["playCount"]:
                parsed_videos.append(video)

        print(f"📊 成功解析 {len(parsed_videos)} 个视频")

        # 按播放量排序
        def parse_count(s):
            s = s.replace("万", "0000").replace(".", "")
            try:
                return int(s)
            except:
                return 0

        parsed_videos.sort(key=lambda v: parse_count(v["playCount"]), reverse=True)

        # 显示 Top 10
        print("\n🔥 Top 10 视频:")
        print(f"{'#':>3} | {'标题':<40} | {'播放':>8} | {'点赞':>5} | {'评论':>4} | {'分享':>4}")
        print("-" * 80)
        for idx, v in enumerate(parsed_videos[:10], 1):
            print(f"{idx:>3} | {v['title'][:40]:<40} | {v['playCount']:>8} | {v['diggCount']:>5} | {v['commentCount']:>4} | {v['shareCount']:>4}")

        # 计算总播放量
        total_play = sum(parse_count(v["playCount"]) for v in parsed_videos)
        print(f"\n📈 总播放量: {total_play:,}")

        # 保存
        output = {
            "account": "泽铭聊无人机",
            "fetch_time": datetime.now().isoformat(),
            "total_videos": len(parsed_videos),
            "total_play_count": total_play,
            "videos": parsed_videos,
        }

        output_path = os.path.join(DATA_DIR, "videos_data.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n💾 数据已保存到: {output_path}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(extract_videos())
