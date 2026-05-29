#!/usr/bin/env python3
"""Render Omnia feature showcase video from screenshots using ffmpeg."""

import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).parent / "omnia-feature-showcase"
ASSETS_DIR = PROJECT_DIR / "assets"
OUTPUT_DIR = PROJECT_DIR / "output"
FPS = 30
WIDTH = 1920
HEIGHT = 1080

# Scene order and durations
SCENES = [
    ("screenshot-hook.png", 3),
    ("screenshot-memory-palace.png", 6),
    ("screenshot-neural-graph.png", 6),
    ("screenshot-tool-execution.png", 6),
    ("screenshot-streaming-chat.png", 4),
    ("screenshot-multi-turn.png", 6),
    ("screenshot-hook.png", 3),  # CTA repeat
]

def create_scene_video(image_path, duration, output_path, fps=30):
    """Create a video clip from a single image with fade in/out."""
    total_frames = int(duration * fps)
    
    # Use ffmpeg to create video from image with zoompan effect
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
            f"zoompan=z='min(zoom+0.0005,1.05)':d={total_frames}:s={WIDTH}x{HEIGHT}:fps={fps},"
            f"fade=t=in:st=0:d=0.5,fade=t=out:st={duration-0.5}:d=0.5"
        ),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        "-preset", "fast",
        "-crf", "20",
        str(output_path)
    ]
    return subprocess.run(cmd, capture_output=True, text=True)

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=== Omnia Feature Showcase Video Renderer ===\n")
    
    # Create individual scene clips
    scene_clips = []
    for i, (image_name, duration) in enumerate(SCENES):
        image_path = ASSETS_DIR / image_name
        if not image_path.exists():
            print(f"❌ Missing: {image_path}")
            continue
        
        clip_path = OUTPUT_DIR / f"clip_{i:02d}.mp4"
        print(f"  [{i+1}/{len(SCENES)}] {image_name} -> {duration}s")
        
        result = create_scene_video(image_path, duration, clip_path)
        if result.returncode == 0:
            scene_clips.append(clip_path)
            print(f"    ✓ Created: {clip_path.name}")
        else:
            print(f"    ❌ Error: {result.stderr[:200]}")
    
    # Concatenate all clips
    print(f"\nConcatenating {len(scene_clips)} clips...")
    
    concat_file = OUTPUT_DIR / "concat.txt"
    with open(concat_file, "w") as f:
        for clip in scene_clips:
            f.write(f"file '{clip}'\n")
    
    final_video = OUTPUT_DIR / "omnia-showcase.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "18",
        str(final_video)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        size_mb = final_video.stat().st_size / (1024 * 1024)
        total_duration = sum(d for _, d in SCENES)
        print(f"\n✅ Video saved: {final_video}")
        print(f"   Size: {size_mb:.1f} MB")
        print(f"   Duration: {total_duration}s")
        print(f"   Resolution: {WIDTH}x{HEIGHT}")
    else:
        print(f"❌ ffmpeg error: {result.stderr[:500]}")

if __name__ == "__main__":
    main()
