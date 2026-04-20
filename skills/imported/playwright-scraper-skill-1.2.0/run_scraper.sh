#!/bin/bash
cd "$(dirname "$0")"
SAVE_HTML=true SCREENSHOT_PATH=/tmp/qianfan_doc.png node scripts/playwright-stealth.js "https://cloud.baidu.com/doc/qianfan/s/imlg0beiu"