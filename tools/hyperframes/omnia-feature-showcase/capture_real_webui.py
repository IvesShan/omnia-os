#!/usr/bin/env python3
"""Capture real Omnia WebUI screenshots using Playwright."""

import os
from playwright.sync_api import sync_playwright

def capture_screenshots():
    output_dir = '/home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase/src/assets/images'
    os.makedirs(output_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Navigate to WebUI
        page.goto('http://localhost:8765')
        page.wait_for_timeout(3000)
        
        # Full page screenshot
        page.screenshot(path=os.path.join(output_dir, 'real-webui-full.png'), full_page=False)
        print('✅ Captured: real-webui-full.png')
        
        # Memory Palace section
        page.evaluate("document.querySelector('[data-section=\"memory\"]')?.scrollIntoView()")
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(output_dir, 'real-memory-palace.png'), full_page=False)
        print('✅ Captured: real-memory-palace.png')
        
        # Neural Graph section
        page.evaluate("document.querySelector('[data-section=\"graph\"]')?.scrollIntoView()")
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(output_dir, 'real-neural-graph.png'), full_page=False)
        print('✅ Captured: real-neural-graph.png')
        
        # Chat area
        page.evaluate("document.querySelector('[data-section=\"chat\"]')?.scrollIntoView()")
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(output_dir, 'real-chat-area.png'), full_page=False)
        print('✅ Captured: real-chat-area.png')
        
        browser.close()
        print('\n🎉 All screenshots captured!')

if __name__ == '__main__':
    capture_screenshots()
