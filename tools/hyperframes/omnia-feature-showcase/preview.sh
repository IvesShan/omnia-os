#!/bin/bash

# Omnia Feature Showcase - 快速预览脚本
# 使用方法: ./preview.sh

set -e

PROJECT_DIR="/home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase"
HYPERFRAMES="/home/shan/.nvm/versions/node/v22.22.3/bin/hyperframes"

echo "🎬 Omnia Feature Showcase - 快速预览"
echo "===================================="
echo ""

# 检查项目目录
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# 检查 hyperframes 命令
if ! command -v "$HYPERFRAMES" &> /dev/null; then
    echo "❌ hyperframes 命令不可用"
    exit 1
fi

echo "📁 项目目录: $PROJECT_DIR"
echo ""

# 显示项目信息
echo "📊 项目信息:"
echo "  - 名称: Omnia Feature Showcase"
echo "  - 分辨率: 1920×1080"
echo "  - 时长: 90秒"
echo "  - 场景: 8个"
echo ""

# 检查输出文件
if [ -f "out/omnia-showcase.mp4" ]; then
    SIZE=$(du -h out/omnia-showcase.mp4 | cut -f1)
    echo "✅ 已有渲染视频: out/omnia-showcase.mp4 ($SIZE)"
    echo ""
    echo "选择操作:"
    echo "  1. 预览视频 (浏览器)"
    echo "  2. 启动预览服务器"
    echo "  3. 重新渲染视频"
    echo "  4. 退出"
    echo ""
    read -p "请选择 (1-4): " choice
    
    case $choice in
        1)
            echo "🌐 在浏览器中打开视频..."
            if command -v xdg-open &> /dev/null; then
                xdg-open "out/omnia-showcase.mp4"
            elif command -v open &> /dev/null; then
                open "out/omnia-showcase.mp4"
            else
                echo "请手动打开: $PROJECT_DIR/out/omnia-showcase.mp4"
            fi
            ;;
        2)
            echo "🚀 启动预览服务器..."
            echo "访问: http://localhost:8080"
            "$HYPERFRAMES" preview --port 8080
            ;;
        3)
            echo "🎬 重新渲染视频..."
            "$HYPERFRAMES" render --output out/omnia-showcase.mp4 --quality standard
            echo "✅ 渲染完成!"
            ;;
        4)
            echo "👋 再见!"
            exit 0
            ;;
        *)
            echo "❌ 无效选择"
            exit 1
            ;;
    esac
else
    echo "⚠️  未找到渲染视频"
    echo ""
    echo "选择操作:"
    echo "  1. 启动预览服务器"
    echo "  2. 渲染视频"
    echo "  3. 退出"
    echo ""
    read -p "请选择 (1-3): " choice
    
    case $choice in
        1)
            echo "🚀 启动预览服务器..."
            echo "访问: http://localhost:8080"
            "$HYPERFRAMES" preview --port 8080
            ;;
        2)
            echo "🎬 渲染视频..."
            "$HYPERFRAMES" render --output out/omnia-showcase.mp4 --quality standard
            echo "✅ 渲染完成!"
            ;;
        3)
            echo "👋 再见!"
            exit 0
            ;;
        *)
            echo "❌ 无效选择"
            exit 1
            ;;
    esac
fi
