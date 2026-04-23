#!/bin/bash
# Omnia 完整打包脚本
# 生成可发布的安装包

set -e

VERSION="1.1.1"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
RELEASE_DIR="$PROJECT_DIR/release"
DIST_DIR="$PROJECT_DIR/src-tauri/target/release/bundle"

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║              Omnia $VERSION 打包构建                        ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"

# 清理旧的发布目录
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# 1. 构建前端 (Tauri)
echo ""
echo "▶ 步骤 1/4: 构建 Tauri 前端..."
cd "$PROJECT_DIR/src-tauri"
cargo tauri build --release

# 2. 打包后端 (PyInstaller)
echo ""
echo "▶ 步骤 2/4: 打包 Python 后端..."
cd "$PROJECT_DIR/backend"

# 检查 PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "安装 PyInstaller..."
    pip install pyinstaller
fi

# 打包后端
pyinstaller --onefile --name omnia-backend standalone_main.py

# 3. 组装发布包
echo ""
echo "▶ 步骤 3/4: 组装发布包..."

# 创建发布目录结构
mkdir -p "$RELEASE_DIR/omnia-$VERSION"
mkdir -p "$RELEASE_DIR/omnia-$VERSION/backend"
mkdir -p "$RELEASE_DIR/omnia-$VERSION/config"
mkdir -p "$RELEASE_DIR/omnia-$VERSION/web"

# 复制前端
if [ -f "$DIST_DIR/appimage/omnia_${VERSION}_amd64.AppImage" ]; then
    cp "$DIST_DIR/appimage/omnia_${VERSION}_amd64.AppImage" "$RELEASE_DIR/omnia-$VERSION/"
    echo "✓ AppImage 已复制"
elif [ -f "$DIST_DIR/deb/omnia_${VERSION}_amd64.deb" ]; then
    cp "$DIST_DIR/deb/omnia_${VERSION}_amd64.deb" "$RELEASE_DIR/omnia-$VERSION/"
    echo "✓ deb 包已复制"
fi

# 复制后端
if [ -f "$PROJECT_DIR/backend/dist/omnia-backend" ]; then
    cp "$PROJECT_DIR/backend/dist/omnia-backend" "$RELEASE_DIR/omnia-$VERSION/backend/"
    echo "✓ 后端已打包"
fi

# 复制 Web 静态文件
cp -r "$PROJECT_DIR/web"/* "$RELEASE_DIR/omnia-$VERSION/web/" 2>/dev/null || true
echo "✓ Web 静态文件已复制"

# 复制配置
cp -r "$PROJECT_DIR/config"/* "$RELEASE_DIR/omnia-$VERSION/config/" 2>/dev/null || true
echo "✓ 配置文件已复制"

# 复制安装脚本
if [ -f "$PROJECT_DIR/install.sh" ]; then
    cp "$PROJECT_DIR/install.sh" "$RELEASE_DIR/omnia-$VERSION/"
    chmod +x "$RELEASE_DIR/omnia-$VERSION/install.sh"
fi

# 复制 README
cp "$PROJECT_DIR/README.md" "$RELEASE_DIR/omnia-$VERSION/" 2>/dev/null || true

# 4. 打包
echo ""
echo "▶ 步骤 4/4: 创建压缩包..."
cd "$RELEASE_DIR"
tar -czvf "omnia-$VERSION-linux-x64.tar.gz" "omnia-$VERSION"

# 生成 SHA256 校验
sha256sum "omnia-$VERSION-linux-x64.tar.gz" > "omnia-$VERSION-linux-x64.tar.gz.sha256"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                    打包完成! 🎉                                      ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║  发布包: $RELEASE_DIR/omnia-$VERSION-linux-x64.tar.gz"
echo "║  大小: $(du -h "$RELEASE_DIR/omnia-$VERSION-linux-x64.tar.gz" | cut -f1)"
echo "╚══════════════════════════════════════════════════════════════════════╝"
