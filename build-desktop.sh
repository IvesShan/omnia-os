#!/bin/bash
# Omnia Desktop - Production Build
# 构建生产版本

cd "$(dirname "$0")"

echo "🔨 Building Omnia Desktop..."
echo ""

npm run tauri build

echo ""
echo "✅ Build complete!"
echo "📦 Binary location: src-tauri/target/release/omnia-desktop"
