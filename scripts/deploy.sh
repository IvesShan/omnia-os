#!/usr/bin/env bash
# ============================================================
#  Omnia 一键部署脚本 — 跨平台 (Linux/macOS)
#  用法: bash deploy.sh
#  要求: 先把 omnia-os/ 整个目录拷贝到目标电脑
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step() { echo -e "\n${CYAN}[$1/$5]${NC} $2"; }
print_ok()   { echo -e "  ${GREEN}✅${NC} $1"; }
print_warn() { echo -e "  ${YELLOW}⚠️${NC} $1"; }
print_err()  { echo -e "  ${RED}❌${NC} $1"; }

# ----- 检测项目根目录 -----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ----- 检测操作系统 -----
OS_TYPE=""
case "$(uname)" in
    Linux)  OS_TYPE="linux"  ;;
    Darwin) OS_TYPE="macos"  ;;
    *)
        print_err "不支持的操作系统: $(uname)"
        echo "  仅支持 Linux 和 macOS"
        exit 1
        ;;
esac

VENV_DIR="$PROJECT_ROOT/venv"

echo ""
echo "  ██████╗ ███╗   ███╗███╗   ██╗██╗ █████╗ "
echo " ██╔═══██╗████╗ ████║████╗  ██║██║██╔══██╗"
echo " ██║   ██║██╔████╔██║██╔██╗ ██║██║███████║"
echo " ██║   ██║██║╚██╔╝██║██║╚██╗██║██║██╔══██║"
echo " ╚██████╔╝██║ ╚═╝ ██║██║ ╚████║██║██║  ██║"
echo "  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝"
echo "     一键部署脚本"
echo ""
echo -e "项目路径: ${CYAN}$PROJECT_ROOT${NC}"
echo -e "系统类型: ${CYAN}$OS_TYPE${NC}"
echo ""

# ===== 1. 检查环境 =====
TOTAL_STEPS=8
print_step 1 "检查运行环境" $TOTAL_STEPS

if ! command -v python3 &> /dev/null; then
    print_err "未找到 Python3，请先安装 Python 3.10+"
    exit 1
fi

# 用 Python 自己检查版本（兼容所有平台，不依赖 grep -P）
python3 -c "
import sys
v = sys.version_info
if v.major < 3 or (v.major == 3 and v.minor < 10):
    sys.exit(1)
sys.exit(0)
" 2>/dev/null || {
    PY_VER=$(python3 --version 2>&1)
    print_err "Python 版本过低: $PY_VER，需要 3.10+"
    exit 1
}

print_ok "$(python3 --version 2>&1)"

if ! command -v pip3 &> /dev/null; then
    print_err "未找到 pip3"
    exit 1
fi
print_ok "pip3 可用"

# macOS 额外检查
if [ "$OS_TYPE" = "macos" ]; then
    if ! command -v lsof &> /dev/null; then
        print_warn "未找到 lsof（端口检查将跳过）"
    else
        print_ok "lsof 可用"
    fi
fi

# ===== 2. 创建虚拟环境 =====
print_step 2 "创建 Python 虚拟环境" $TOTAL_STEPS

if [ -d "$VENV_DIR" ]; then
    print_warn "虚拟环境已存在，跳过"
else
    python3 -m venv "$VENV_DIR"
    print_ok "虚拟环境已创建: $VENV_DIR"
fi

# ===== 3. 安装依赖 =====
print_step 3 "安装 Python 依赖" $TOTAL_STEPS

source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    pip install -r "$PROJECT_ROOT/requirements.txt" -q
    print_ok "依赖安装完成"
else
    print_warn "未找到 requirements.txt"
fi

# ===== 4. 创建必要目录 =====
print_step 4 "创建运行时目录" $TOTAL_STEPS

mkdir -p "$PROJECT_ROOT/data" "$PROJECT_ROOT/logs" "$PROJECT_ROOT/.omnia"
print_ok "data/ logs/ .omnia/ 已就绪"

# ===== 5. 配置环境变量 =====
print_step 5 "配置环境变量 (.env)" $TOTAL_STEPS

if [ -f "$PROJECT_ROOT/.env" ]; then
    print_warn ".env 已存在，跳过（如需修改请手动编辑）"
else
    cat > "$PROJECT_ROOT/.env" << 'ENVEOF'
# Omnia 配置文件
# 请填入你的 API 密钥

# === OpenAI 兼容 API（默认使用本地 Ollama）===
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=http://localhost:11434/v1

# === 可选：飞书配置 ===
# FEISHU_APP_ID=
# FEISHU_APP_SECRET=
ENVEOF
    print_ok ".env 已创建（请编辑填入 API 密钥）"
    print_warn "不要忘记修改 .env 文件！"
fi

# ===== 6. 配置服务（自动检测系统） =====
print_step 6 "配置系统服务" $TOTAL_STEPS

if [ "$OS_TYPE" = "linux" ]; then
    # ---- Linux: systemd ----
    SYSTEMD_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SYSTEMD_DIR"

    # omnia.service — Web 服务
    cat > "$SYSTEMD_DIR/omnia.service" << SERVEOF
[Unit]
Description=Omnia Agent OS
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
ExecStart=$VENV_DIR/bin/python3 src/omnia/web_server.py
Restart=always
RestartSec=5
StandardOutput=append:$PROJECT_ROOT/logs/web_server.log
StandardError=append:$PROJECT_ROOT/logs/web_server.log

[Install]
WantedBy=default.target
SERVEOF

    # omnia-daemon.service — AI 守护进程
    cat > "$SYSTEMD_DIR/omnia-daemon.service" << SERVEOF
[Unit]
Description=Omnia Daemon - AI Operating System Core
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
ExecStart=$VENV_DIR/bin/python3 -u $PROJECT_ROOT/scripts/start_daemon.py
Restart=always
RestartSec=10
OOMScoreAdjust=-500
Nice=5
StandardOutput=append:$PROJECT_ROOT/logs/daemon.log
StandardError=append:$PROJECT_ROOT/logs/daemon.log

[Install]
WantedBy=default.target
SERVEOF

    # omnia-watchdog.service — 健康监控
    cat > "$SYSTEMD_DIR/omnia-watchdog.service" << SERVEOF
[Unit]
Description=Omnia Watchdog - Health Monitor
After=omnia-daemon.service
Requires=omnia-daemon.service

[Service]
Type=simple
ExecStart=$VENV_DIR/bin/python3 $PROJECT_ROOT/scripts/watchdog.py
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_ROOT/logs/watchdog.log
StandardError=append:$PROJECT_ROOT/logs/watchdog.log

[Install]
WantedBy=default.target
SERVEOF

    systemctl --user daemon-reload
    print_ok "3 个 systemd 服务已创建"

else
    # ---- macOS: launchd ----
    LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$LAUNCH_AGENTS_DIR"

    # 卸载已有的同名 plist（防止冲突）
    for label in com.omnia.web com.omnia.daemon com.omnia.watchdog; do
        launchctl unload "$LAUNCH_AGENTS_DIR/$label.plist" 2>/dev/null || true
    done

    # com.omnia.web.plist — Web 服务
    cat > "$LAUNCH_AGENTS_DIR/com.omnia.web.plist" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.omnia.web</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python3</string>
        <string>$PROJECT_ROOT/src/omnia/web_server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/logs/web_server.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/logs/web_server.log</string>
</dict>
</plist>
PLISTEOF

    # com.omnia.daemon.plist — 守护进程
    cat > "$LAUNCH_AGENTS_DIR/com.omnia.daemon.plist" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.omnia.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python3</string>
        <string>-u</string>
        <string>$PROJECT_ROOT/scripts/start_daemon.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/logs/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/logs/daemon.log</string>
    <key>Nice</key>
    <integer>5</integer>
</dict>
</plist>
PLISTEOF

    # com.omnia.watchdog.plist — 看门狗
    cat > "$LAUNCH_AGENTS_DIR/com.omnia.watchdog.plist" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.omnia.watchdog</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python3</string>
        <string>$PROJECT_ROOT/scripts/watchdog.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_ROOT</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_ROOT/logs/watchdog.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_ROOT/logs/watchdog.log</string>
</dict>
</plist>
PLISTEOF

    print_ok "3 个 launchd plist 已创建"
fi

# ===== 7. 启用并启动 =====
print_step 7 "启用并启动服务" $TOTAL_STEPS

if [ "$OS_TYPE" = "linux" ]; then
    systemctl --user enable omnia.service omnia-daemon.service omnia-watchdog.service 2>/dev/null
    print_ok "开机自启已启用"

    systemctl --user start omnia.service omnia-daemon.service omnia-watchdog.service 2>/dev/null || {
        print_warn "部分服务启动可能延迟，请稍后检查"
    }
    print_ok "服务已启动"
else
    # macOS: 加载 plist（load = 启动 + 开机自启）
    launchctl load "$LAUNCH_AGENTS_DIR/com.omnia.web.plist" 2>/dev/null || true
    launchctl load "$LAUNCH_AGENTS_DIR/com.omnia.daemon.plist" 2>/dev/null || true
    launchctl load "$LAUNCH_AGENTS_DIR/com.omnia.watchdog.plist" 2>/dev/null || true
    print_ok "服务已启动（登录时自动加载）"
fi

sleep 3

# ===== 8. 验证 =====
print_step 8 "验证部署" $TOTAL_STEPS

ALL_OK=true

if [ "$OS_TYPE" = "linux" ]; then
    for s in omnia omnia-daemon omnia-watchdog; do
        STATUS=$(systemctl --user is-active "$s" 2>/dev/null)
        if [ "$STATUS" = "active" ]; then
            print_ok "$s → 运行中"
        else
            print_err "$s → $STATUS"
            ALL_OK=false
        fi
    done
    sleep 2
    if ss -tlnp 2>/dev/null | grep -q ":5001"; then
        print_ok "Web 服务 (5001) → 监听中"
    else
        print_warn "Web 服务 (5001) → 未检测到（可能还在启动）"
    fi
else
    # macOS: 用 launchctl list + lsof 验证
    for label in com.omnia.web com.omnia.daemon com.omnia.watchdog; do
        OUT=$(launchctl list "$label" 2>/dev/null || echo "not_found")
        PID=$(echo "$OUT" | awk 'NR==2{print $1}' 2>/dev/null)
        if [ "$OUT" = "not_found" ]; then
            print_err "$label → 未加载"
            ALL_OK=false
        elif [ "$PID" = "-1" ]; then
            print_warn "$label → 已加载但进程退出（会自动重启）"
        elif [ -n "$PID" ]; then
            print_ok "$label → 运行中 (PID: $PID)"
        fi
    done
    sleep 2
    if lsof -i :5001 -P -n 2>/dev/null | grep -q LISTEN; then
        print_ok "Web 服务 (5001) → 监听中"
    else
        print_warn "Web 服务 (5001) → 未检测到（可能还在启动）"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$ALL_OK" = true ]; then
    echo -e "  ${GREEN}✅ Omnia 部署成功！${NC}"
else
    echo -e "  ${YELLOW}⚠️  Omnia 部署完成，但部分服务异常${NC}"
    echo -e "  运行 ${CYAN}bash scripts/manage.sh status${NC} 查看详情"
fi
echo ""
echo -e "  ${CYAN}访问地址:${NC}  http://localhost:5001"
echo -e "  ${CYAN}管理命令:${NC}  bash scripts/manage.sh status"
echo ""
echo -e "  ${CYAN}常用命令:${NC}"
echo "    bash scripts/manage.sh        查看状态"
echo "    bash scripts/manage.sh logs    查看日志"
echo "    bash scripts/manage.sh restart 重启服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
