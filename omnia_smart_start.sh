#!/bin/bash
# Omnia 智能启动脚本（FastAPI 版本）
# 避免进程冲突

echo "🔍 检查 Omnia FastAPI 状态..."

# 检查端口
if ss -tlnp | grep -q ":8765"; then
    echo "✅ Omnia FastAPI 已在运行 (端口 8765)"
    echo ""
    echo "进程信息:"
    ps aux | grep -E 'uvicorn.*src.omnia.main' | grep -v grep
    
    echo ""
    echo "测试访问:"
    curl -s http://localhost:8765/api/status | head -c 200
    
    exit 0
fi

echo "🧹 清理旧进程..."
pkill -9 -f "uvicorn.*src.omnia.main" 2>/dev/null
sleep 2

echo ""
echo "🚀 启动 Omnia FastAPI..."
cd ~/omnia-os

# 启动 FastAPI Server
nohup python3 -m uvicorn src.omnia.main:app --host 0.0.0.0 --port 8765 > /tmp/omnia_fastapi.log 2>&1 &

sleep 3

echo ""
echo "=== 进程状态 ==="
ps aux | grep uvicorn | grep -v grep

echo ""
echo "=== 端口状态 ==="
ss -tlnp | grep 8765

echo ""
echo "✅ Omnia FastAPI 启动完成！"
echo "访问地址: http://localhost:8765"
