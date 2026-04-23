#!/bin/bash
cd "$(dirname "$0")"
pkill -f "python3.*web_server" 2>/dev/null
sleep 1
nohup python3 src/omnia/web_server.py > /tmp/omnia_web.log 2>&1 &
echo "Omnia Web UI started at http://127.0.0.1:5001/"
echo "PID: $!"
