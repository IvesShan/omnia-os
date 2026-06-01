#!/usr/bin/env python3
"""Capture real Omnia WebUI screenshots using Playwright."""

import os
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

OUTPUT_DIR = '/home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase/assets'

def capture_screenshots():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path='/home/shan/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome'
        )
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Navigate to WebUI
        print("🌐 Loading http://localhost:8765 ...")
        page.goto('http://localhost:8765', wait_until='networkidle')
        page.wait_for_timeout(3000)
        
        # 1. Full dashboard screenshot
        page.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-full.png'), full_page=False)
        print('✅ Captured: real-ui-full.png (full dashboard)')
        
        # 2. Memory Palace panel - left sidebar
        memory_panel = page.query_selector('[data-action="memory"]')
        if memory_panel:
            memory_panel.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-memory.png'))
            print('✅ Captured: real-ui-memory.png')
        else:
            print('⚠️  Memory panel not found, capturing fallback')
            page.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-memory.png'), full_page=False)
        
        # 3. Neural Graph panel - right sidebar
        neural_panel = page.query_selector('[data-action="neural-graph"]')
        if neural_panel:
            neural_panel.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-graph.png'))
            print('✅ Captured: real-ui-graph.png')
        else:
            print('⚠️  Neural panel not found, capturing fallback')
            page.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-graph.png'), full_page=False)
        
        # 4. System vitals panel
        sys_panel = page.query_selector('#sys-panel')
        if sys_panel:
            sys_panel.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-system.png'))
            print('✅ Captured: real-ui-system.png')
        
        # 5. Skill matrix panel
        skill_panel = page.query_selector('[data-action="skills"]')
        if skill_panel:
            skill_panel.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-skills.png'))
            print('✅ Captured: real-ui-skills.png')
        
        # 6. Git panel
        git_panel = page.query_selector('[data-action="git"]')
        if git_panel:
            git_panel.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-git.png'))
            print('✅ Captured: real-ui-git.png')
        
        # 7. Workflow panel
        workflow_panel = page.query_selector('[data-action="workflow"]')
        if workflow_panel:
            workflow_panel.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-workflow.png'))
            print('✅ Captured: real-ui-workflow.png')
        
        # 8. API selector panel
        api_panel = page.query_selector('#api-panel')
        if api_panel:
            api_panel.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-api.png'))
            print('✅ Captured: real-ui-api.png')
        
        # 9. Notification panel
        notif_panel = page.query_selector('#notif-panel')
        if notif_panel:
            notif_panel.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-notif.png'))
            print('✅ Captured: real-ui-notif.png')
        
        # 10. Link status panel
        daemon_panel = page.query_selector('[data-action="daemon"]')
        if daemon_panel:
            daemon_panel.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-daemon.png'))
            print('✅ Captured: real-ui-daemon.png')
        
        # 11. Chat area (center) - try to find it
        chat_area = page.query_selector('.chat-area') or page.query_selector('#chat-panel') or page.query_selector('[data-action="chat"]')
        if chat_area:
            chat_area.screenshot(path=os.path.join(OUTPUT_DIR, 'real-ui-chat.png'))
            print('✅ Captured: real-ui-chat.png')
        else:
            print('⚠️  Chat area not found as standalone element, using full dashboard')
        
        browser.close()
        print('\n🎉 All screenshots captured!')
        print(f'📁 Output: {OUTPUT_DIR}')
        
        # List captured files
        for f in sorted(os.listdir(OUTPUT_DIR)):
            if f.startswith('real-ui') and f.endswith('.png'):
                path = os.path.join(OUTPUT_DIR, f)
                size_kb = os.path.getsize(path) / 1024
                print(f'   {f} ({size_kb:.1f} KB)')

if __name__ == '__main__':
    capture_screenshots()
