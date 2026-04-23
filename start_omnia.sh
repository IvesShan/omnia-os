#!/bin/bash
export PATH="/home/shan/.local/bin:$PATH"
export PYTHONPATH="/home/shan/.local/lib/python3.12/site-packages:$PYTHONPATH"
cd "$(dirname "$0")"
# Load .env
set -a
source .env 2>/dev/null || true
set +a
exec python3 src/omnia/web_server.py
