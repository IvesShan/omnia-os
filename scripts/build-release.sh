#!/bin/bash
# Omnia 发布包构建脚本
# 生成可分发的安装包

set -e

OMNIA_VERSION="0.1.0"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_DIR="$PROJECT_ROOT/release"
PACKAGE_NAME="omnia-${OMNIA_VERSION}-linux-x64"

echo "=========================================="
echo "  Omnia 发布包构建 v${OMNIA_VERSION}"
echo "=========================================="
echo ""

# 清理旧的发布目录
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR/$PACKAGE_NAME"

# 1. 构建前端（如果需要）
echo "检查前端构建..."
if [ ! -f "$PROJECT_ROOT/src-tauri/target/release/bundle/appimage/Omnia_${OMNIA_VERSION}_amd64.AppImage" ]; then
    echo "前端未构建，开始构建..."
    cd "$PROJECT_ROOT/src-tauri"
    cargo tauri build
    cd "$PROJECT_ROOT"
fi

# 2. 构建后端（PyInstaller）
echo "打包后端..."
cd "$PROJECT_ROOT/backend"

# 检查 PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "安装 PyInstaller..."
    pip3 install pyinstaller
fi

# 打包后端
pyinstaller --onefile --name omnia-backend omnia_backend.py 2>/dev/null || true

# 3. 复制文件到发布目录
echo "组装发布包..."

# 前端
cp "$PROJECT_ROOT/src-tauri/target/release/bundle/appimage/Omnia_${OMNIA_VERSION}_amd64.AppImage" \
   "$RELEASE_DIR/$PACKAGE_NAME/Omnia"

# 后端
if [ -f "$PROJECT_ROOT/backend/dist/omnia-backend" ]; then
    cp "$PROJECT_ROOT/backend/dist/omnia-backend" "$RELEASE_DIR/$PACKAGE_NAME/"
else
    echo "⚠ PyInstaller 打包失败，使用 Python 源码"
    mkdir -p "$RELEASE_DIR/$PACKAGE_NAME/backend"
    cp -r "$PROJECT_ROOT/backend/"* "$RELEASE_DIR/$PACKAGE_NAME/backend/"
    cp -r "$PROJECT_ROOT/src" "$RELEASE_DIR/$PACKAGE_NAME/"
fi

# 安装脚本
cp "$PROJECT_ROOT/scripts/install.sh" "$RELEASE_DIR/$PACKAGE_NAME/"
cp "$PROJECT_ROOT/scripts/uninstall.sh" "$RELEASE_DIR/$PACKAGE_NAME/"
chmod +x "$RELEASE_DIR/$PACKAGE_NAME/install.sh"
chmod +x "$RELEASE_DIR/$PACKAGE_NAME/uninstall.sh"

# README
cat > "$RELEASE_DIR/$PACKAGE_NAME/README.md" << EOF
# Omnia ${OMNIA_VERSION}

永不遗忘的操作系统

## 安装

\`\`\`bash
./install.sh
\`\`\`

## 使用

\`\`\`bash
omnia          # 启动 Omnia
omnia-backend  # 管理后端服务
\`\`\`

## 配置

首次使用请配置 API Key：

\`\`\`bash
# 编辑配置文件
nano ~/.omnia/config/api_keys.json
\`\`\`

或在应用内配置。

## 卸载

\`\`\`bash
./uninstall.sh
\`\`\`

## 系统要求

- Linux x64
- Python 3.8+
- 至少 1GB 可用空间

## 问题反馈

https://github.com/your-org/omnia/issues
EOF

# 默认配置
mkdir -p "$RELEASE_DIR/$PACKAGE_NAME/config"
cat > "$RELEASE_DIR/$PACKAGE_NAME/config/settings.json" << EOF
{
  "backend": {
    "port": 5001,
    "auto_start": true,
    "log_level": "info"
  },
  "api": {
    "default_model": "ernie-4.0-8k",
    "provider": "baidu"
  },
  "memory": {
    "max_entries": 10000
  }
}
EOF

# 4. 创建压缩包
echo "创建压缩包..."
cd "$RELEASE_DIR"
tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"

# 5. 生成校验和
sha256sum "${PACKAGE_NAME}.tar.gz" > "${PACKAGE_NAME}.tar.gz.sha256"

# 6. 清理
rm -rf "$PACKAGE_NAME"

echo ""
echo "=========================================="
echo "  ✓ 发布包构建完成！"
echo "=========================================="
echo ""
echo "发布包位置："
echo "  $RELEASE_DIR/${PACKAGE_NAME}.tar.gz"
echo ""
echo "大小：$(du -h "$RELEASE_DIR/${PACKAGE_NAME}.tar.gz" | cut -f1)"
echo ""
echo "分发命令："
echo "  scp ${PACKAGE_NAME}.tar.gz user@server:~"
echo "  tar -xzf ${PACKAGE_NAME}.tar.gz"
echo "  cd ${PACKAGE_NAME}"
echo "  ./install.sh"
echo ""
