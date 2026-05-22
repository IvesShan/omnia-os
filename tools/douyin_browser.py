#!/usr/bin/env python3
"""
抖音创作者中心 - Playwright 自动化浏览器
用法:
  python3 douyin_browser.py login     # 打开浏览器等待扫码登录
  python3 douyin_browser.py data      # 获取最新视频数据
"""

import sys
import json
import time
from pathlib import Path

BROWSER_DATA_DIR = "/home/shan/omnia-os/data/browser_data/douyin"
OUTPUT_FILE = "/home/shan/omnia-os/data/douyin_latest.json"


def cmd_login():
    """打开浏览器，等待扫码登录"""
    from playwright.sync_api import sync_playwright

    Path(BROWSER_DATA_DIR).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            BROWSER_DATA_DIR,
            headless=False,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://creator.douyin.com")

        print("浏览器已打开！", flush=True)
        print(f"当前URL: {page.url}", flush=True)

        # 每5秒检查一次是否登录成功（最多等5分钟）
        for i in range(60):
            time.sleep(5)
            url = page.url
            print(f"[{(i+1)*5}s] URL: {url}", flush=True)

            if "creator-micro" in url or (url.rstrip("/") == "https://creator.douyin.com"):
                try:
                    body = page.inner_text("body")
                    if "扫码" not in body[:500]:
                        print("✅ 登录成功！保存登录状态...", flush=True)
                        context.close()
                        print("DONE", flush=True)
                        return
                except:
                    pass

        print("⏰ 等待超时", flush=True)
        context.close()


def cmd_data():
    """获取最新视频数据"""
    from playwright.sync_api import sync_playwright

    Path(BROWSER_DATA_DIR).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            BROWSER_DATA_DIR,
            headless=False,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        page = context.pages[0] if context.pages else context.new_page()
        results = {}

        # 1. 内容管理页
        print("正在获取视频列表...", flush=True)
        page.goto("https://creator.douyin.com/creator-micro/content/manage")
        time.sleep(6)
        url = page.url
        print(f"URL: {url}", flush=True)

        if "login" in url.lower():
            body = page.inner_text("body")[:500]
            if "扫码" in body:
                print("ERROR: 未登录，请先运行 login", flush=True)
                context.close()
                return

        results["content_manage"] = page.inner_text("body")[:8000]

        # 2. 数据中心
        print("正在获取数据中心...", flush=True)
        page.goto("https://creator.douyin.com/creator-micro/data")
        time.sleep(6)
        results["data_center"] = page.inner_text("body")[:5000]

        # 3. 粉丝数据
        print("正在获取粉丝数据...", flush=True)
        page.goto("https://creator.douyin.com/creator-micro/fans")
        time.sleep(6)
        results["fans"] = page.inner_text("body")[:3000]

        # 保存
        Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 数据已保存到: {OUTPUT_FILE}", flush=True)
        print("\n=== 内容管理页（前3000字）===", flush=True)
        print(results["content_manage"][:3000], flush=True)
        print("\n=== 数据中心（前2000字）===", flush=True)
        print(results["data_center"][:2000], flush=True)

        context.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "login"

    if cmd == "login":
        cmd_login()
    elif cmd == "data":
        cmd_data()
    else:
        print(f"未知命令: {cmd}")
        print("用法: python3 douyin_browser.py [login|data]")
