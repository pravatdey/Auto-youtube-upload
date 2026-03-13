"""Split a video into equal-duration parts using FFmpeg segment muxer."""

import os
import subprocess

from utils.ffprobe import get_video_info


def split_video(input_path: str, output_dir: str, segment_duration: int = 900) -> list[str]:
    """Split a video into parts of specified duration.

    Args:
        input_path: Path to the video file to split
        output_dir: Directory to save the parts
        segment_duration: Duration of each part in seconds (default: 900 = 15 min)

    Returns:
        Sorted list of output file paths
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input video not found: {input_path}")

    os.makedirs(output_dir, exist_ok=True)

    info = get_video_info(input_path)
    duration = info["duration"]
    num_parts = max(1, int(duration / segment_duration) + (1 if duration % segment_duration > 0 else 0))

    print(f"Splitting {duration:.1f}s video into ~{num_parts} parts ({segment_duration}s each)")

    # Get base name without extension
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_pattern = os.path.join(output_dir, f"{base_name}_part_%03d.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-c", "copy",              # No re-encoding (input already processed)
        "-map", "0",
        "-segment_time", str(segment_duration),
        "-reset_timestamps", "1",
        "-f", "segment",
        output_pattern,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg split failed: {result.stderr}")

    # Collect output files
    parts = sorted(
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.startswith(f"{base_name}_part_") and f.endswith(".mp4")
    )

    print(f"Created {len(parts)} parts in {output_dir}/")
    for p in parts:
        size = os.path.getsize(p) / (1024 * 1024)
        print(f"  {os.path.basename(p)} ({size:.1f} MB)")

    return parts
