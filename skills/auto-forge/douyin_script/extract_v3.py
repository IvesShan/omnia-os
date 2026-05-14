#!/usr/bin/env python3
"""从抖音创作者后台提取视频数据 v3"""

import asyncio
import json
import os
import re
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


async def extract():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9267")
        context = browser.contexts[0]
        page = await context.new_page()
        
        await page.goto(
            "https://creator.douyin.com/creator-micro/content/manage",
            wait_until="networkidle",
            timeout=30000,
        )
        await asyncio.sleep(3)

        for i in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

        text = await page.evaluate("() => document.body.innerText")
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # 解析视频数据
        # 抖音创作者后台格式:
        # [标题行] - 视频标题（长文本）
        # [时长行] - 如 "02:25"
        # [时间行] - 如 "2026年05月03日 09:48"
        # [状态行] - "已发布"
        # 播放
        # [数字]
        # 点赞
        # [数字]
        # 评论
        # [数字]
        # 分享
        # [数字]

        videos = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # 找到以"播放"开头的行
            if line == "播放":
                # 回溯找标题（从播放行往上找）
                title = ""
                publish_time = ""
                duration = ""

                for offset in range(1, 15):
                    if i - offset >= 0:
                        prev = lines[i - offset]
                        # 跳过已知的操作行
                        if prev in ["已发布", "编辑作品", "设置权限", "置顶", "删除作品", "已智能生成章节要点，确认并添加，可以使视频结构更清晰"]:
                            continue
                        # 跳过只有数字的行（播放量等）
                        if re.match(r"^\d+\.?\d*万?$", prev):
                            continue
                        # 跳过 "点赞" "评论" "分享"
                        if prev in ["点赞", "评论", "分享"]:
                            continue
                        # 匹配时间行
                        time_match = re.search(r"(\d{4}年\d{2}月\d{2}日\s*\d{2}:\d{2})", prev)
                        if time_match:
                            publish_time = time_match.group(1)
                            continue
                        # 匹配时长行 (如 "02:25")
                        if re.match(r"^\d{1,2}:\d{2}$", prev):
                            duration = prev
                            continue
                        # 剩下的就是标题
                        if len(prev) > 5 and not title:
                            title = prev

                # 获取播放量（下一行）
                play_count = ""
                if i + 1 < len(lines):
                    play_count = lines[i + 1]

                # 找点赞、评论、分享
                digg_count = ""
                comment_count = ""
                share_count = ""

                for offset in range(1, 12):
                    if i + offset < len(lines):
                        if lines[i + offset] == "点赞" and i + offset + 1 < len(lines):
                            digg_count = lines[i + offset + 1]
                        elif lines[i + offset] == "评论" and i + offset + 1 < len(lines):
                            comment_count = lines[i + offset + 1]
                        elif lines[i + offset] == "分享" and i + offset + 1 < len(lines):
                            share_count = lines[i + offset + 1]

                if play_count:
                    videos.append(
                        {
                            "title": title,
                            "duration": duration,
                            "publishTime": publish_time,
                            "playCount": play_count,
                            "diggCount": digg_count,
                            "commentCount": comment_count,
                            "shareCount": share_count,
                        }
                    )

            i += 1

        # 转换数字
        def parse_count(s):
            if not s:
                return 0
            s = s.replace("万", "0000")
            if "." in s:
                parts = s.split(".")
                if len(parts) == 2:
                    s = parts[0] + parts[1][:4].ljust(4, "0")
            try:
                return int(s)
            except:
                return 0

        videos.sort(key=lambda v: parse_count(v["playCount"]), reverse=True)

        total_play = sum(parse_count(v["playCount"]) for v in videos)
        total_digg = sum(parse_count(v["diggCount"]) for v in videos)
        total_comment = sum(parse_count(v["commentCount"]) for v in videos)
        total_share = sum(parse_count(v["shareCount"]) for v in videos)

        print(f"\n{'='*60}")
        print(f"📊 账号: 泽铭聊无人机")
        print(f"{'='*60}")
        print(f"总视频数: {len(videos)}")
        print(f"总播放量: {total_play:,}")
        print(f"总点赞数: {total_digg:,}")
        print(f"总评论数: {total_comment:,}")
        print(f"总分享数: {total_share:,}")
        print(f"{'='*60}\n")

        print(f"{'#':>3} | {'标题':<50} | {'播放':>8} | {'点赞':>5} | {'评论':>4} | {'分享':>4}")
        print("-" * 90)
        for idx, v in enumerate(videos[:15], 1):
            title_short = v["title"][:48] if v["title"] else "(无标题)"
            print(
                f"{idx:>3} | {title_short:<50} | {v['playCount']:>8} | {v['diggCount']:>5} | {v['commentCount']:>4} | {v['shareCount']:>4}"
            )

        if len(videos) > 15:
            print(f"... 还有 {len(videos) - 15} 个视频")

        # 保存
        output = {
            "account": "泽铭聊无人机",
            "fetch_time": datetime.now().isoformat(),
            "total_videos": len(videos),
            "total_play_count": total_play,
            "total_digg_count": total_digg,
            "total_comment_count": total_comment,
            "total_share_count": total_share,
            "videos": videos,
        }

        output_path = os.path.join(DATA_DIR, "videos_data.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n💾 数据已保存到: {output_path}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(extract())
