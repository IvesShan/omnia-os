#!/bin/bash
# Omnia 守护进程优化脚本
# 降低内存占用，防止被系统杀掉

OMNIA_HOME="$HOME/.omnia"
PID_FILE="$OMNIA_HOME/daemon.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "❌ 守护进程未运行"
    exit 1
fi

PID=$(cat "$PID_FILE")

echo "🔧 优化守护进程 (PID: $PID)..."

# 1. 降低 OOM score（减少被杀概率）
# -1000 表示"尽量不杀"，0 是默认，1000 是"优先杀"
echo "📊 调整 OOM score..."
echo -500 > /proc/$PID/oom_score_adj 2>/dev/null || {
    echo "⚠️ 需要 root 权限调整 OOM score"
    echo "   运行: sudo echo -500 > /proc/$PID/oom_score_adj"
}

# 2. 设置进程优先级（降低 CPU 争抢）
echo "⚡ 调整进程优先级..."
renice -n 5 -p $PID 2>/dev/null || echo "⚠️ 无法调整优先级"

# 3. 建议：使用 systemd 服务管理
echo ""
echo "💡 建议：创建 systemd 服务实现自动重启"
echo ""
echo "创建文件: ~/.config/systemd/user/omnia-daemon.service"
echo ""
cat << 'EOF'
[Unit]
Description=Omnia Daemon
After=network.target

[Service]
Type=simple
ExecStart=/home/shan/pytorch_env/bin/python3 -u /home/shan/omnia-os/.omnia/_daemon_runner.py
Restart=always
RestartSec=10
OOMScoreAdjust=-500
Nice=5

[Install]
WantedBy=default.target
EOF

echo ""
echo "启用服务："
echo "  systemctl --user daemon-reload"
echo "  systemctl --user enable omnia-daemon"
echo "  systemctl --user start omnia-daemon"
