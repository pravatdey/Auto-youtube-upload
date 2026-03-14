"""Orchestrates the full FFmpeg video processing pipeline."""

import os
import subprocess
import sys

from pipeline.ffmpeg_filters import build_audio_filters, build_video_filters
from utils.ffprobe import get_video_info


def process_video(input_path: str, output_path: str, config: dict, logo_path: str | None = None) -> str:
    """Process a video: pitch shift + watermark removal + add branding.

    Args:
        input_path: Path to source video file
        output_path: Path for processed output file
        config: Configuration dict from config.yaml
        logo_path: Optional override for logo PNG path

    Returns:
        Path to the processed output file
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input video not found: {input_path}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Get video info for audio sample rate
    info = get_video_info(input_path)
    sample_rate = info.get("sample_rate", 44100)
    duration = info.get("duration", 0)

    print(f"Input: {input_path}")
    print(f"Duration: {duration:.1f}s ({duration / 3600:.1f} hours)")
    print(f"Resolution: {info['width']}x{info['height']}")

    # Build filter chains
    video_args, uses_logo = build_video_filters(config, logo_path, info["width"], info["height"])
    pitch_shift = config.get("pitch_shift", 1.0)
    intro_mute = config.get("intro_mute_duration", 0)
    audio_args = build_audio_filters(pitch_shift, sample_rate, intro_mute)

    # Construct ffmpeg command
    cmd = ["ffmpeg", "-y", "-i", input_path]

    # Add logo as second input if needed
    effective_logo = logo_path or config.get("logo_path")
    if uses_logo and effective_logo:
        cmd.extend(["-i", effective_logo])

    # Add video filters or copy video
    if video_args:
        cmd.extend(video_args)
    else:
        cmd.extend(["-map", "0:v", "-c:v", "copy"])

    # Add audio filters
    cmd.extend(audio_args)

    # Video encoding settings (only if we have video filters, otherwise copy)
    if video_args:
        crf = config.get("crf", 20)
        preset = config.get("preset", "fast")
        cmd.extend(["-c:v", "libx264", "-crf", str(crf), "-preset", preset])

    # Output
    cmd.append(output_path)

    print(f"\nProcessing video...")
    print(f"Pitch shift: {pitch_shift}x")
    if video_args:
        print(f"Video filters active (CRF={config.get('crf', 20)}, preset={config.get('preset', 'fast')})")

    # Print full command for debugging
    print(f"FFmpeg command: {' '.join(cmd)}")

    # Set temp directory to avoid C: drive (may be full)
    env = os.environ.copy()
    temp_dir = config.get("temp_dir")
    if temp_dir:
        os.makedirs(temp_dir, exist_ok=True)
        env["TEMP"] = temp_dir
        env["TMP"] = temp_dir
        env["TMPDIR"] = temp_dir

    # Run ffmpeg with real-time output
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    # Print stderr lines for progress (ffmpeg writes progress to stderr)
    last_time = ""
    stderr_lines = []
    for line in process.stderr:
        line = line.strip()
        stderr_lines.append(line)
        # Show progress lines (contain "time=")
        if "time=" in line:
            # Extract time value for compact progress display
            parts = line.split("time=")
            if len(parts) > 1:
                time_val = parts[1].split(" ")[0]
                if time_val != last_time:
                    last_time = time_val
                    sys.stdout.write(f"\r  Progress: {time_val}  ")
                    sys.stdout.flush()

    process.wait()
    print()  # newline after progress

    if process.returncode != 0:
        # Print last 30 lines of stderr for debugging
        error_output = "\n".join(stderr_lines[-30:])
        print(f"FFmpeg stderr:\n{error_output}", file=sys.stderr)
        raise RuntimeError(f"FFmpeg failed with exit code {process.returncode}")

    output_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Output: {output_path} ({output_size:.1f} MB)")
    return output_path
