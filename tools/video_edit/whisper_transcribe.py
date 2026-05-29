#!/usr/bin/env python3
"""Whisper 语音识别 → SRT 字幕"""
import whisper
import sys
import os

video_path = sys.argv[1] if len(sys.argv) > 1 else "/home/shan/下载/1b84d5d3b5892b1e9c3ec7f2d5f34789.mp4"
out_dir = sys.argv[2] if len(sys.argv) > 2 else "/home/shan/omnia-os/tools/video_edit_output"
model_size = sys.argv[3] if len(sys.argv) > 3 else "small"

os.makedirs(out_dir, exist_ok=True)

print(f"[1] 加载 Whisper {model_size} 模型...")
model = whisper.load_model(model_size)

print(f"[2] 识别中: {video_path}")
result = model.transcribe(video_path, language="zh", word_timestamps=True)

# SRT 格式输出
def format_ts(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

base = os.path.splitext(os.path.basename(video_path))[0]
srt_path = os.path.join(out_dir, f"{base}.srt")
txt_path = os.path.join(out_dir, f"{base}.txt")

with open(srt_path, "w", encoding="utf-8") as f:
    for i, seg in enumerate(result["segments"], 1):
        f.write(f"{i}\n")
        f.write(f"{format_ts(seg['start'])} --> {format_ts(seg['end'])}\n")
        f.write(f"{seg['text'].strip()}\n\n")

with open(txt_path, "w", encoding="utf-8") as f:
    f.write(result["text"])

print(f"[3] ✅ 字幕文件: {srt_path}")
print(f"[3] ✅ 纯文本: {txt_path}")
print(f"[3] 识别结果:\n{result['text'][:1000]}")
print("WHISPER_DONE")
