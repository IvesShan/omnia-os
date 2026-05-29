#!/bin/bash
# HyperFrames 视频渲染脚本 - Omnia 集成
# 用法: ./render.sh <project-name> [--check|--preview|--render]

set -e

# 加载 nvm 并切换到 Node.js 22
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 22 > /dev/null 2>&1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_NAME="${1:-}"
ACTION="${2:---check}"

if [ -z "$PROJECT_NAME" ]; then
    echo "用法: $0 <project-name> [--check|--preview|--render]"
    echo ""
    echo "可用项目:"
    ls -d "$SCRIPT_DIR"/*/ 2>/dev/null | while read dir; do
        name=$(basename "$dir")
        if [ -f "$dir/hyperframes.json" ]; then
            echo "  - $name"
        fi
    done
    exit 1
fi

PROJECT_DIR="$SCRIPT_DIR/$PROJECT_NAME"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ 项目不存在: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

case "$ACTION" in
    --check)
        echo "🔍 检查项目: $PROJECT_NAME"
        npx hyperframes lint 2>&1
        ;;
    --preview)
        echo "👁️ 预览项目: $PROJECT_NAME (http://localhost:3000)"
        npm run dev 2>&1
        ;;
    --render)
        echo "🎬 渲染项目: $PROJECT_NAME → MP4"
        npm run render 2>&1
        echo "✅ 渲染完成！输出文件在: $PROJECT_DIR/out/"
        ls -la out/ 2>/dev/null || true
        ;;
    --snapshot)
        echo "📸 截取关键帧: $PROJECT_NAME"
        npx hyperframes snapshot 2>&1
        ;;
    *)
        echo "❌ 未知操作: $ACTION"
        echo "可用: --check, --preview, --render, --snapshot"
        exit 1
        ;;
esac
