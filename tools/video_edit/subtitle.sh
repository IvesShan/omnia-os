#!/bin/bash
# 口播视频自动字幕流水线
# 用法: bash tools/video_edit/subtitle.sh <input.mp4> [output.mp4]
# 依赖: whisper (语音转字幕), ffmpeg (视频处理)

set -e

INPUT="$1"
if [ -z "$INPUT" ] || [ ! -f "$INPUT" ]; then
    echo "❌ 用法: bash tools/video_edit/subtitle.sh <input.mp4> [output.mp4]"
    exit 1
fi

FILENAME=$(basename "$INPUT" | sed 's/\.[^.]*$//')
OUTPUT="${2:-${FILENAME}_subtitled.mp4}"
SRT_FILE="/tmp/${FILENAME}.srt"
WHISPER_VENV="$HOME/venvs/whisper/bin/activate"

echo "🎤 Step 1: 语音识别 → 生成字幕..."
if [ -f "$WHISPER_VENV" ]; then
    source "$WHISPER_VENV"
    whisper "$INPUT" --model small --language zh --output_format srt --output_dir /tmp/
else
    echo "⚠️  Whisper 未安装，尝试安装..."
    pip install openai-whisper --break-system-packages 2>/dev/null || {
        echo "❌ Whisper 安装失败"
        exit 1
    }
    whisper "$INPUT" --model small --language zh --output_format srt --output_dir /tmp/
fi

# whisper 输出文件名
SRT_FILE="/tmp/${FILENAME}.srt"
if [ ! -f "$SRT_FILE" ]; then
    echo "❌ 字幕文件未生成: $SRT_FILE"
    exit 1
fi
echo "✅ 字幕已生成: $SRT_FILE"

echo "🔤 Step 2: 烧录字幕到视频..."
ffmpeg -y -i "$INPUT" \
    -vf "subtitles=${SRT_FILE}:force_style='FontName=Noto Sans SC,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,Alignment=2,MarginV=60'" \
    -c:a copy \
    "$OUTPUT"

echo "✅ 完成: $OUTPUT"
echo "📊 文件大小: $(du -h "$OUTPUT" | cut -f1)"
