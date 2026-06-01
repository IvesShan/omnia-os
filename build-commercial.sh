#!/bin/bash
# ============================================================
# Omnia 商业版打包脚本 v2.0
# 支持 Linux / macOS / Windows (via cross-compilation)
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 版本号
VERSION=${1:-$(grep -oP 'version = "\K[^"]+' src-tauri/tauri.conf.json 2>/dev/null || grep -oP '"version": "\K[^"]+' src-tauri/tauri.conf.json || echo "1.2.0")}
BUILD_DATE=$(date +%Y%m%d)
BUILD_DIR="build/commercial"
DIST_DIR="dist/v${VERSION}"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║        Omnia 商业版打包系统 v2.0                      ║"
echo "║        版本: v${VERSION}                                  ║"
echo "║        日期: ${BUILD_DATE}                               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================
# 检查依赖
# ============================================================
echo -e "${BLUE}[1/6] 检查构建依赖...${NC}"

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}✗ $1 未安装${NC}"
        return 1
    else
        echo -e "${GREEN}✓ $1 已安装${NC}"
        return 0
    fi
}

MISSING=0
check_command python3 || MISSING=1
check_command pip3 || MISSING=1
check_command node || MISSING=1

# 检查 Nuitka
if ! python3 -c "import nuitka" 2>/dev/null; then
    echo -e "${YELLOW}⚠ Nuitka 未安装，正在安装...${NC}"
    pip3 install nuitka ordered-set
fi

# 检查 Tauri CLI
if ! command -v cargo &> /dev/null; then
    echo -e "${YELLOW}⚠ Rust/Cargo 未安装（Tauri 桌面构建需要）${NC}"
    echo -e "${YELLOW}  桌面应用构建将跳过，请使用 GitHub Actions 构建${NC}"
    SKIP_TAURI=1
else
    SKIP_TAURI=0
    if ! command -v tauri &> /dev/null; then
        echo -e "${YELLOW}⚠ Tauri CLI 未安装，正在安装...${NC}"
        cargo install tauri-cli
    fi
fi

if [ $MISSING -eq 1 ]; then
    echo -e "${RED}缺少必要依赖，请先安装${NC}"
    exit 1
fi

# ============================================================
# 清理旧的构建
# ============================================================
echo -e "\n${BLUE}[2/6] 清理旧构建...${NC}"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}" "${DIST_DIR}"

# ============================================================
# 构建 Python 后端（Nuitka）
# ============================================================
echo -e "\n${BLUE}[3/6] 构建 Python 后端 (Nuitka)...${NC}"

# 检测当前平台
OS=$(uname -s)
ARCH=$(uname -m)

case "$OS" in
    Linux*)  PLATFORM="linux" ;;
    Darwin*) PLATFORM="macos" ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
    *) echo -e "${RED}不支持的平台: $OS${NC}"; exit 1 ;;
esac

echo -e "${CYAN}平台: ${PLATFORM}-${ARCH}${NC}"

# 构建后端
python3 -m nuitka \
    --standalone \
    --onefile \
    --output-filename=omnia-backend \
    --output-dir="${BUILD_DIR}/backend" \
    --include-package=src \
    --include-package=core \
    --include-module=flask \
    --include-module=flask_cors \
    --include-module=uvicorn \
    --include-module=sqlite3 \
    --include-data-dir=seeds=seeds \
    --include-data-dir=config=config \
    --noinclude-default-plugin \
    backend/standalone_main.py \
    2>&1 | tail -20

if [ -f "${BUILD_DIR}/backend/omnia-backend" ] || [ -f "${BUILD_DIR}/backend/omnia-backend.exe" ]; then
    echo -e "${GREEN}✓ 后端构建成功${NC}"
    BACKEND_SIZE=$(du -sh "${BUILD_DIR}/backend/omnia-backend"* 2>/dev/null | cut -f1)
    echo -e "${CYAN}  大小: ${BACKEND_SIZE}${NC}"
else
    echo -e "${RED}✗ 后端构建失败${NC}"
    exit 1
fi

# ============================================================
# 准备前端资源
# ============================================================
echo -e "\n${BLUE}[4/6] 准备前端资源...${NC}"

# 复制前端文件
cp -r web "${BUILD_DIR}/web"
cp -r seeds "${BUILD_DIR}/seeds"
cp -r config "${BUILD_DIR}/config"
cp -r src "${BUILD_DIR}/src"

echo -e "${GREEN}✓ 前端资源已复制${NC}"

# ============================================================
# 创建安装包
# ============================================================
echo -e "\n${BLUE}[5/6] 创建安装包...${NC}"

PACKAGE_NAME="omnia-v${VERSION}-${PLATFORM}-${ARCH}"

# 创建安装目录结构
INSTALL_DIR="${BUILD_DIR}/${PACKAGE_NAME}"
mkdir -p "${INSTALL_DIR}/bin"
mkdir -p "${INSTALL_DIR}/web"
mkdir -p "${INSTALL_DIR}/seeds"
mkdir -p "${INSTALL_DIR}/config"

# 复制后端
cp "${BUILD_DIR}/backend/omnia-backend"* "${INSTALL_DIR}/bin/"
chmod +x "${INSTALL_DIR}/bin/omnia-backend"* 2>/dev/null || true

# 复制前端
cp -r web/* "${INSTALL_DIR}/web/"

# 复制种子数据
cp -r seeds/* "${INSTALL_DIR}/seeds/"

# 复制配置模板
cp -r config/* "${INSTALL_DIR}/config/" 2>/dev/null || true

# 复制授权系统
cp -r src "${INSTALL_DIR}/src"

# 创建启动脚本
cat > "${INSTALL_DIR}/start.sh" << 'STARTEOF'
#!/bin/bash
# Omnia 启动脚本
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 启动后端
echo "正在启动 Omnia..."
./bin/omnia-backend --port 5001 --host 127.0.0.1 &

# 等待后端启动
sleep 3

# 打开浏览器
if command -v xdg-open &> /dev/null; then
    xdg-open http://127.0.0.1:5001
elif command -v open &> /dev/null; then
    open http://127.0.0.1:5001
fi

echo "Omnia 已启动！访问 http://127.0.0.1:5001"
echo "按 Ctrl+C 停止"
wait
STARTEOF
chmod +x "${INSTALL_DIR}/start.sh"

# 创建 Windows 启动脚本
cat > "${INSTALL_DIR}/start.bat" << 'STARTEOF'
@echo off
title Omnia AIOS
echo 正在启动 Omnia...
start /B bin\omnia-backend.exe --port 5001 --host 127.0.0.1
timeout /t 3 /nobreak > nul
start http://127.0.0.1:5001
echo Omnia 已启动！访问 http://127.0.0.1:5001
echo 按 Ctrl+C 停止
pause
STARTEOF

# 创建 README
cat > "${INSTALL_DIR}/README.md" << READMEEOF
# Omnia AIOS v${VERSION}

## 快速开始

### Linux / macOS
\`\`\`bash
chmod +x start.sh
./start.sh
\`\`\`

### Windows
双击 \`start.bat\`

## 首次使用

1. 启动后访问 http://127.0.0.1:5001
2. 首次打开会进入**授权激活页面**
3. 输入卡密激活，或点击"免费试用1天"
4. 配置 AI 服务商 API Key
5. 开始使用！

## 定价

| 类型 | 价格 | 有效期 |
|------|------|--------|
| 试用版 | 免费 | 1 天 |
| 月卡 | ¥68 | 30 天 |
| 季卡 | ¥168 | 90 天 |
| 年卡 | ¥388 | 365 天 |
| 终身版 | ¥888 | 永久 |

## 技术支持

- 邮箱: support@omnia-ai.com
- 官网: https://omnia-ai.com
READMEEOF

# 打包
cd "${BUILD_DIR}"
if [ "$PLATFORM" = "windows" ]; then
    zip -r "../../${DIST_DIR}/${PACKAGE_NAME}.zip" "${PACKAGE_NAME}/"
    echo -e "${GREEN}✓ 已创建: ${DIST_DIR}/${PACKAGE_NAME}.zip${NC}"
else
    tar -czf "../../${DIST_DIR}/${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}/"
    echo -e "${GREEN}✓ 已创建: ${DIST_DIR}/${PACKAGE_NAME}.tar.gz${NC}"
fi
cd ../..

# ============================================================
# 构建 Tauri 桌面应用（如果 Rust 可用）
# ============================================================
if [ $SKIP_TAURI -eq 0 ]; then
    echo -e "\n${BLUE}[6/6] 构建 Tauri 桌面应用...${NC}"
    
    # 复制后端到 Tauri 资源目录
    mkdir -p src-tauri/binaries
    cp "${BUILD_DIR}/backend/omnia-backend"* src-tauri/binaries/
    
    # 构建 Tauri
    cd src-tauri
    cargo tauri build
    cd ..
    
    # 复制产物
    cp -r src-tauri/target/release/bundle/*.deb "${DIST_DIR}/" 2>/dev/null || true
    cp -r src-tauri/target/release/bundle/*.AppImage "${DIST_DIR}/" 2>/dev/null || true
    cp -r src-tauri/target/release/bundle/*.dmg "${DIST_DIR}/" 2>/dev/null || true
    cp -r src-tauri/target/release/bundle/*.msi "${DIST_DIR}/" 2>/dev/null || true
    cp -r src-tauri/target/release/bundle/*.exe "${DIST_DIR}/" 2>/dev/null || true
    
    echo -e "${GREEN}✓ Tauri 桌面应用构建完成${NC}"
else
    echo -e "\n${YELLOW}[6/6] 跳过 Tauri 桌面构建（Rust 未安装）${NC}"
    echo -e "${YELLOW}  请使用 GitHub Actions 构建桌面应用${NC}"
fi

# ============================================================
# 生成校验和
# ============================================================
echo -e "\n${BLUE}生成校验和...${NC}"
cd "${DIST_DIR}"
sha256sum * > checksums.txt 2>/dev/null || shasum -a 256 * > checksums.txt
cd ../..

# ============================================================
# 完成
# ============================================================
echo -e "\n${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        ✅ 打包完成！                                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo -e ""
echo -e "${CYAN}产物目录: ${DIST_DIR}/${NC}"
echo -e ""
ls -lh "${DIST_DIR}/"
echo -e ""
echo -e "${CYAN}下一步:${NC}"
echo -e "  1. 测试安装包"
echo -e "  2. 生成卡密: python3 tools/keygen.py --type monthly --count 10"
echo -e "  3. 上传到 GitHub Releases"
echo -e "  4. 分发给用户"
echo -e ""
