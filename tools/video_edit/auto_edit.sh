#!/bin/bash
# ============================================================
# 口播视频自动剪辑流水线 v2
# 用法: bash auto_edit.sh input.mp4 [brand_text] [subtitle_style] [tagline] [cn_sub]
# 示例: bash auto_edit.sh 口播.mp4 "无人机维修" tiktok "Drone Repair Expert" "专业 · 值得信赖"
# ============================================================

set -e

INPUT="$1"
BRAND="${2:-OMNIA}"
STYLE="${3:-tiktok}"
TAGLINE="${4:-Your AI Super Assistant}"
CN_SUB="${5:-全能 · 智能 · 记忆}"

if [ -z "$INPUT" ]; then
    echo "用法: bash auto_edit.sh <input.mp4> [brand_text] [subtitle_style] [tagline] [cn_sub]"
    echo "  subtitle_style: tiktok | classic | minimal"
    exit 1
fi

WORKDIR="/home/shan/omnia-os"
TOOLSDIR="$WORKDIR/tools/video_edit"
OUTDIR="$WORKDIR/tools/video_edit_output"
HFDIR="$WORKDIR/tools/hyperframes"
HFPROJECT="$HFDIR/omnia-brand-intros"
INPUT_ABS=$(realpath "$INPUT")
FILENAME=$(basename "$INPUT" | sed 's/\.[^.]*$//')
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

mkdir -p "$OUTDIR"

echo "========================================"
echo "  口播视频自动剪辑 v2"
echo "========================================"
echo "  输入: $INPUT"
echo "  品牌: $BRAND"
echo "  标语: $TAGLINE"
echo "  副标题: $CN_SUB"
echo "  字幕风格: $STYLE"
echo "========================================"

# ---- Step 1: Whisper 语音转字幕 ----
echo ""
echo "[1/4] 🎤 Whisper 语音识别..."
VENV="$WORKDIR/venv/bin/activate"
source "$VENV" 2>/dev/null || . "$VENV"

SRT_FILE="$OUTDIR/${FILENAME}.srt"
if [ -f "$SRT_FILE" ]; then
    echo "  ⏩ 字幕文件已存在，跳过识别: $SRT_FILE"
else
    whisper "$INPUT_ABS" \
        --model small \
        --language zh \
        --output_dir "$OUTDIR" \
        --output_format srt \
        --word_timestamps True \
        2>&1 | tail -5
    echo "  ✅ 字幕生成: $SRT_FILE"
fi

# ---- Step 2: FFmpeg 烧录字幕到视频 ----
echo ""
echo "[2/4] 📝 FFmpeg 烧录字幕（风格: $STYLE）..."

SRT_ESCAPED=$(echo "$SRT_FILE" | sed "s/'/\\\\'/g")

case "$STYLE" in
    tiktok)
        STYLE_OPTS="FontSize=18,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,Bold=1,Alignment=2,MarginV=60"
        ;;
    classic)
        STYLE_OPTS="FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=40"
        ;;
    minimal)
        STYLE_OPTS="FontSize=15,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=3,Outline=0,Shadow=0,Alignment=2,MarginV=50"
        ;;
    *)
        echo "  ⚠️ 未知风格 $STYLE，使用默认 tiktok"
        STYLE_OPTS="FontSize=18,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,Bold=1,Alignment=2,MarginV=60"
        ;;
esac

SUBTITLED="$OUTDIR/${FILENAME}_subtitled.mp4"
ffmpeg -y -i "$INPUT_ABS" \
    -vf "subtitles=${SRT_ESCAPED}:force_style='FontName=Noto Sans CJK SC,${STYLE_OPTS}'" \
    -c:v libx264 -preset fast -crf 23 \
    -c:a copy \
    "$SUBTITLED" 2>&1 | tail -3

echo "  ✅ 字幕视频: $SUBTITLED"

# ---- Step 3: HyperFrames 生成片头动画 ----
echo ""
echo "[3/4] 🎬 HyperFrames 生成片头动画..."

# Use the omnia-brand-intros HyperFrames project with --variables
HF_INTRO_OUT="$OUTDIR/${FILENAME}_intro"
mkdir -p "$HF_INTRO_OUT"

# Get absolute path for the output
HF_INTRO_OUT_ABS=$(realpath "$HF_INTRO_OUT")

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 22 > /dev/null 2>&1

cd "$HFPROJECT"
/home/shan/omnia-os/tools/hyperframes/node_modules/.bin/hyperframes render \
    -o "$HF_INTRO_OUT_ABS/intro.mp4" \
    --variables "{\"brand\":\"${BRAND}\",\"tagline\":\"${TAGLINE}\",\"cnSub\":\"${CN_SUB}\"}" \
    2>&1 | tail -8

INTRO_MP4="$HF_INTRO_OUT/intro.mp4"
if [ -f "$INTRO_MP4" ]; then
    echo "  ✅ 片头动画: $INTRO_MP4"
else
    echo "  ⚠️ 片头生成失败，跳过拼接"
    INTRO_MP4=""
fi

# ---- Step 4: FFmpeg 拼接 ----
echo ""
if [ -n "$INTRO_MP4" ] && [ -f "$INTRO_MP4" ]; then
    echo "[4/4] 🔗 FFmpeg 拼接：片头 + 口播(带字幕)..."

    # 获取口播视频的尺寸
    VID_W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of default=nw=1:nk=1 "$SUBTITLED")
    VID_H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=nw=1:nk=1 "$SUBTITLED")
    echo "  口播视频尺寸: ${VID_W}x${VID_H}"

    TEMP_INTRO="$OUTDIR/_temp_intro.mp4"
    TEMP_SUBTITLED="$OUTDIR/_temp_subtitled.mp4"

    # 片头缩放到和口播视频一致的尺寸
    ffmpeg -y -i "$INTRO_MP4" \
        -vf "scale=${VID_W}:${VID_H}:force_original_aspect_ratio=decrease,pad=${VID_W}:${VID_H}:(ow-iw)/2:(oh-ih)/2:color=black" \
        -c:v libx264 -preset fast -crf 23 \
        -an \
        "$TEMP_INTRO" 2>/dev/null

    # 口播视频确保参数一致
    ffmpeg -y -i "$SUBTITLED" \
        -vf "scale=${VID_W}:${VID_H}:force_original_aspect_ratio=decrease,pad=${VID_W}:${VID_H}:(ow-iw)/2:(oh-ih)/2:color=black" \
        -c:v libx264 -preset fast -crf 23 \
        -c:a aac -b:a 128k \
        "$TEMP_SUBTITLED" 2>/dev/null

    # 创建拼接列表
    echo "file '$TEMP_INTRO'" > "$OUTDIR/_concat.txt"
    echo "file '$TEMP_SUBTITLED'" >> "$OUTDIR/_concat.txt"

    FINAL="$OUTDIR/${FILENAME}_final_${TIMESTAMP}.mp4"
    ffmpeg -y -f concat -safe 0 -i "$OUTDIR/_concat.txt" \
        -c:v libx264 -preset fast -crf 23 \
        -c:a aac -b:a 128k \
        "$FINAL" 2>/dev/null

    # 清理临时文件
    rm -f "$TEMP_INTRO" "$TEMP_SUBTITLED" "$OUTDIR/_concat.txt"

    echo ""
    echo "========================================"
    echo "  ✅ 完成！最终视频："
    echo "  📁 $FINAL"
    echo "========================================"
    echo ""
    echo "  中间产物："
    echo "    📝 字幕: $SRT_FILE"
    echo "    🎞️ 带字幕: $SUBTITLED"
    echo "    🎬 片头: $INTRO_MP4"
    echo ""
else
    echo "[4/4] ⚠️ 无片头，跳过拼接"
    FINAL="$SUBTITLED"
    echo ""
    echo "========================================"
    echo "  ✅ 完成！带字幕视频："
    echo "  📁 $FINAL"
    echo "========================================"
fi
