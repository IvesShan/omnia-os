#!/bin/bash
# 批量渲染所有片头模板，用于预览效果

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/previews"
mkdir -p "$OUTPUT_DIR"

TEMPLATES=(
  "tech_glitch:科技故障风"
  "minimal_gradient:极简渐变风"
  "particle_reveal:粒子揭示风"
  "cinematic_zoom:电影缩放风"
  "typewriter:代码编辑器风"
)

echo "🎬 开始渲染模板预览..."
echo "输出目录: $OUTPUT_DIR"
echo ""

for item in "${TEMPLATES[@]}"; do
  IFS=':' read -r template name <<< "$item"
  input="$SCRIPT_DIR/templates/$template/index.html"
  output="$OUTPUT_DIR/${template}_preview.mp4"
  
  if [ ! -f "$input" ]; then
    echo "⚠️  跳过: $input 不存在"
    continue
  fi
  
  echo "▶️  渲染 [$name] ..."
  hyperframes render \
    --input "$input" \
    --output "$output" \
    --width 720 \
    --height 1280 \
    --duration 3 \
    --fps 30 \
    2>/dev/null && echo "✅ 完成: $output" || echo "❌ 失败: $template"
  echo ""
done

echo "🎉 全部渲染完成！预览文件在 $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR"
