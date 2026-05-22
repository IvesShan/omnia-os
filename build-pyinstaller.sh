#!/bin/bash
# ============================================================
# Omnia PyInstaller 打包脚本（修复版）
# ============================================================

set -e

echo "🔨 Omnia PyInstaller 打包开始..."
echo "============================================"

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 激活虚拟环境
if [ -d "venv" ]; then
    echo "✓ 激活虚拟环境..."
    . venv/bin/activate
fi

# 清理旧的构建
rm -rf build
rm -rf dist/omnia-backend-dist

echo ""
echo "🔧 使用 PyInstaller 打包..."
echo "============================================"

# PyInstaller 打包（使用绝对路径）
pyinstaller \
    --onefile \
    --noconsole \
    --name omnia-backend \
    --distpath "$PROJECT_ROOT/dist/omnia-backend-dist" \
    --workpath "$PROJECT_ROOT/build/pyinstaller-build" \
    --specpath "$PROJECT_ROOT/build" \
    --add-data "$PROJECT_ROOT/seeds:seeds" \
    --add-data "$PROJECT_ROOT/config:config" \
    --add-data "$PROJECT_ROOT/web:web" \
    --add-data "$PROJECT_ROOT/skills:skills" \
    --hidden-import flask \
    --hidden-import flask_cors \
    --hidden-import json \
    --hidden-import logging \
    "$PROJECT_ROOT/backend/standalone_main.py"

echo ""
echo "✅ PyInstaller 打包完成！"
echo ""

# 创建输出目录
mkdir -p dist/omnia-backend

# 复制产物
cp dist/omnia-backend-dist/omnia-backend dist/omnia-backend/
chmod +x dist/omnia-backend/omnia-backend

# 复制资源文件
cp -r seeds dist/omnia-backend/
cp -r config dist/omnia-backend/
cp -r web dist/omnia-backend/
cp -r skills dist/omnia-backend/

# 创建启动脚本
cat > dist/omnia-backend/start-omnia.sh << 'STARTEOF'
#!/bin/bash
cd "$(dirname "$0")"
./omnia-backend --port 5001
STARTEOF
chmod +x dist/omnia-backend/start-omnia.sh

# 创建 README
cat > dist/omnia-backend/README.md << 'READMEEOF'
# Omnia Backend - PyInstaller 打包版

## 启动方式

```bash
./start-omnia.sh
```

## 目录结构

```
omnia-backend/
├── omnia-backend      # 主程序（单文件）
├── seeds/             # 人格设定
├── config/            # 配置模板
├── web/               # 前端UI
├── skills/            # 技能包
└── start-omnia.sh     # 启动脚本
```

## 用户数据

首次启动会自动创建 `~/.omnia/` 目录存储用户数据。

## API 端口

默认端口：5001
READMEEOF

echo "============================================"
echo "📦 打包产物位置: dist/omnia-backend/"
echo ""
echo "文件列表:"
ls -lh dist/omnia-backend/
echo ""
echo "============================================"
echo "✅ 打包完成！"
