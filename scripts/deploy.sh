#!/bin/bash
# ============================================================
#  Omnia 一键部署脚本
#  给别人的电脑用的 — 全自动部署
#  用法: bash deploy.sh
#  要求: 先把 omnia-os/ 整个目录拷贝到目标电脑
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step() { echo -e "\n${CYAN}[$1/$4]${NC} $2"; }
print_ok()   { echo -e "  ${GREEN}✅${NC} $1"; }
print_warn() { echo -e "  ${YELLOW}⚠️${NC} $1"; }
print_err()  { echo -e "  ${RED}❌${NC} $1"; }

# ----- 检测项目根目录 -----
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "  ██████╗ ███╗   ███╗███╗   ██╗██╗ █████╗ "
echo " ██╔═══██╗████╗ ████║████╗  ██║██║██╔══██╗"
echo " ██║   ██║██╔████╔██║██╔██╗ ██║██║███████║"
echo " ██║   ██║██║╚██╔╝██║██║╚██╗██║██║██╔══██║"
echo " ╚██████╔╝██║ ╚═╝ ██║██║ ╚████║██║██║  ██║"
echo "  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝"
echo "     一键部署脚本"
echo ""
echo "项目路径: $PROJECT_ROOT"
echo ""

# ===== 1. 检查环境 =====
TOTAL_STEPS=8
print_step 1 "检查运行环境" $TOTAL_STEPS

if ! command -v python3 &> /dev/null; then
    print_err "未找到 Python3，请先安装 Python 3.10+"
    exit 1
fi

PY_VER=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
if [ "$(echo "$PY_VER >= 3.10" | bc 2>/dev/null)" != "1" ]; then
    # bc might not be available, fallback check
    MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$MAJOR" -lt 3 ] || [ "$MAJOR" -eq 3 -a "$MINOR" -lt 10 ]; then
        print_err "Python 版本过低: $PY_VER，需要 3.10+"
        exit 1
    fi
fi
print_ok "Python $PY_VER"

if ! command -v pip3 &> /dev/null; then
    print_err "未找到 pip3"
    exit 1
fi
print_ok "pip3 可用"

# ===== 2. 创建虚拟环境 =====
print_step 2 "创建 Python 虚拟环境" $TOTAL_STEPS

VENV_DIR="$PROJECT_ROOT/venv"
if [ -d "$VENV_DIR" ]; then
    print_warn "虚拟环境已存在，跳过"
else
    python3 -m venv "$VENV_DIR"
    print_ok "虚拟环境已创建"
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

# ===== 6. 配置 systemd 用户服务 =====
print_step 6 "配置 systemd 服务（开机自启）" $TOTAL_STEPS

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
StandardOutput=append:/tmp/omnia.log
StandardError=append:/tmp/omnia.log

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
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
SERVEOF

systemctl --user daemon-reload
print_ok "3 个 systemd 服务已创建"

# ===== 7. 启用并启动 =====
print_step 7 "启用并启动服务" $TOTAL_STEPS

systemctl --user enable omnia.service omnia-daemon.service omnia-watchdog.service 2>/dev/null
print_ok "开机自启已启用"

systemctl --user start omnia.service omnia-daemon.service omnia-watchdog.service 2>/dev/null
print_ok "服务已启动"

# 等待启动完成
sleep 3

# ===== 8. 验证 =====
print_step 8 "验证部署" $TOTAL_STEPS

# 检查服务状态
ALL_OK=true
for s in omnia omnia-daemon omnia-watchdog; do
    STATUS=$(systemctl --user is-active "$s" 2>/dev/null)
    if [ "$STATUS" = "active" ]; then
        print_ok "$s → 运行中"
    else
        print_err "$s → $STATUS"
        ALL_OK=false
    fi
done

# 检查端口
sleep 2
if ss -tlnp 2>/dev/null | grep -q ":5001"; then
    print_ok "Web 服务 (5001) → 监听中"
else
    print_warn "Web 服务 (5001) → 未检测到（可能还在启动）"
    print_warn "稍后手动检查: systemctl --user status omnia"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$ALL_OK" = true ]; then
    echo -e "  ${GREEN}✅ Omnia 部署成功！${NC}"
else
    echo -e "  ${YELLOW}⚠️  Omnia 部署完成，但部分服务异常${NC}"
fi
echo ""
echo "  访问地址:  http://localhost:5001"
echo "  管理命令:  cd $PROJECT_ROOT && bash scripts/manage.sh status"
echo ""
echo "  常用命令:"
echo "    bash scripts/manage.sh status   查看状态"
echo "    bash scripts/manage.sh logs     查看日志"
echo "    bash scripts/manage.sh restart  重启服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
