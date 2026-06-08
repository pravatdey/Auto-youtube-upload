"""Complete branding removal & replacement using FFmpeg filters.

Removes all StudyIQ branding (top-right icon, intro text) from video using
FFmpeg's delogo/drawbox/overlay filters. Replaces original intro with your
custom intro, changes voice pitch, adds your watermark and text overlay.

Usage:
    python -m pipeline.rebrand "C:/Users/PravatkumarDey/Downloads/videoplayback.mp4"
    python -m pipeline.rebrand "video.mp4" --intro "my_intro.mp4"
"""

import argparse
import os
import subprocess
import sys


def _run_ffmpeg(cmd: list[str], label: str = "FFmpeg"):
    """Run an FFmpeg command with real-time progress display."""
    env = os.environ.copy()
    env["TEMP"] = "D:/temp"
    env["TMP"] = "D:/temp"

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env, encoding="utf-8", errors="replace",
    )

    last_time = ""
    stderr_lines = []
    for line in process.stderr:
        line = line.strip()
        stderr_lines.append(line)
        if "time=" in line:
            parts = line.split("time=")
            if len(parts) > 1:
                time_val = parts[1].split(" ")[0]
                if time_val != last_time:
                    last_time = time_val
                    sys.stdout.write(f"\r  {label}: {time_val}  ")
                    sys.stdout.flush()

    process.wait()
    print()

    if process.returncode != 0:
        error_output = "\n".join(stderr_lines[-30:])
        print(f"\n{label} stderr:\n{error_output}", file=sys.stderr)
        raise RuntimeError(f"{label} failed with exit code {process.returncode}")


def _probe_video(path: str) -> dict:
    """Get video dimensions, sample rate, and duration."""
    # Dimensions
    result = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x", path,
    ], capture_output=True, text=True)
    dims = result.stdout.strip().split("x")
    w = int(dims[0]) if len(dims) >= 2 else 640
    h = int(dims[1]) if len(dims) >= 2 else 360

    # Sample rate
    result2 = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ], capture_output=True, text=True)
    sr = int(result2.stdout.strip()) if result2.stdout.strip() else 44100

    # Duration
    result3 = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ], capture_output=True, text=True)
    dur = float(result3.stdout.strip()) if result3.stdout.strip() else 0

    return {"width": w, "height": h, "sample_rate": sr, "duration": dur}


def _chain_atempo(factor: float) -> list[str]:
    """Chain atempo filters to stay within [0.5, 100.0] range."""
    filters = []
    while factor < 0.5:
        filters.append("atempo=0.5")
        factor /= 0.5
    while factor > 100.0:
        filters.append("atempo=100.0")
        factor /= 100.0
    filters.append(f"atempo={factor:.6f}")
    return filters


def process_video_rebrand(input_path: str, output_path: str, watermark_path: str,
                          pitch_shift: float = 1.15,
                          custom_text: str = "Civil Services & Competitive Exam Prep",
                          intro_path: str | None = None,
                          outro_path: str | None = None,
                          trim_intro_sec: float = 28.0,
                          trim_end_at: float | None = None,
                          upscale_to: int | None = None):
    """Remove all StudyIQ branding and replace with yours.

    Args:
        input_path: Source video path
        output_path: Final output path
        watermark_path: Your watermark PNG
        pitch_shift: Audio pitch multiplier
        custom_text: Text overlay at bottom-left
        intro_path: Your custom intro video (prepended to output)
        outro_path: Your custom outro/subscription video (appended to output)
        trim_intro_sec: Seconds of original intro to remove (default 28s)
        trim_end_at: Cut the video at this timestamp (removes end promo)
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Video not found: {input_path}")
    if not os.path.isfile(watermark_path):
        raise FileNotFoundError(f"Watermark not found: {watermark_path}")
    if intro_path and not os.path.isfile(intro_path):
        raise FileNotFoundError(f"Intro video not found: {intro_path}")
    if outro_path and not os.path.isfile(outro_path):
        raise FileNotFoundError(f"Outro video not found: {outro_path}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    temp_dir = os.path.dirname(output_path) or "."

    info = _probe_video(input_path)
    w, h = info["width"], info["height"]
    sample_rate = info["sample_rate"]

    print("=" * 60)
    print("REBRANDING VIDEO - Complete StudyIQ Removal")
    print("=" * 60)
    print(f"Input:     {input_path} ({info['duration']:.1f}s, {w}x{h})")
    print(f"Watermark: {watermark_path}")
    print(f"Pitch:     {pitch_shift}x")
    print(f"Text:      {custom_text}")
    if intro_path:
        intro_info = _probe_video(intro_path)
        print(f"Intro:     {intro_path} ({intro_info['duration']:.1f}s)")
        print(f"Trim start: first {trim_intro_sec}s removed")
    if outro_path:
        outro_info = _probe_video(outro_path)
        print(f"Outro:     {outro_path} ({outro_info['duration']:.1f}s)")
    if trim_end_at:
        print(f"Trim end:  cut at {trim_end_at}s (removes end promo)")
    print()

    # =====================================================================
    # STEP 1: Process main video (trim intro + delogo + watermark + pitch)
    # =====================================================================
    print("STEP 1: Processing main video (remove branding, pitch shift)...")

    # --- delogo pixel values (must be strictly inside frame) ---
    # Delogo runs on source resolution (w x h)
    # StudyIQ logo spans ~78% to right edge, ~17% height
    dl_x = int(w * 0.78)
    dl_y = 1
    dl_w = w - dl_x - 2
    dl_h = int(h * 0.17) - 1

    # Video filter chain
    vf_parts = []

    # 1. Remove StudyIQ logo — delogo blends with surrounding pixels (no black box)
    vf_parts.append(f"delogo=x={dl_x}:y={dl_y}:w={dl_w}:h={dl_h}:show=0")

    # 3. Upscale to target resolution if requested (after delogo for cleaner output)
    if upscale_to and upscale_to > h:
        # Preserve aspect ratio: height = upscale_to, width = proportional
        target_h = upscale_to
        target_w = int(w * target_h / h)
        # Round to even for H.264
        target_w = target_w - (target_w % 2)
        target_h = target_h - (target_h % 2)
        vf_parts.append(f"scale={target_w}:{target_h}:flags=lanczos")
        out_w, out_h = target_w, target_h
        print(f"  Upscaling: {w}x{h} -> {target_w}x{target_h} (lanczos)")
    else:
        out_w, out_h = w, h

    video_filter = ",".join(vf_parts)

    # Build overlay filter with watermark + text — sized for output resolution
    escaped_text = custom_text.replace("'", "\\'").replace(":", "\\:")
    font_path = "assets/fonts/arial.ttf"
    # Scale watermark and text based on output size
    wm_width = int(out_w * 0.15)
    text_size = max(18, int(out_h * 0.04))  # 4% of height, min 18
    overlay_filter = (
        f"[0:v]{video_filter}[cleaned];"
        f"[1:v]scale={wm_width}:-1[wm];"
        f"[cleaned][wm]overlay=W-w-5:5[with_logo];"
        f"[with_logo]drawtext="
        f"fontfile={font_path}:"
        f"text='{escaped_text}':"
        f"fontcolor=white@0.85:"
        f"fontsize={text_size}:"
        f"x=10:y=h-th-10:"
        f"box=1:boxcolor=black@0.5:boxborderw=5[v_out]"
    )

    filter_script = os.path.join(temp_dir, "_filter.txt")
    with open(filter_script, "w", encoding="utf-8") as f:
        f.write(overlay_filter)

    # Audio filter: pitch shift
    af_parts = []
    if pitch_shift != 1.0:
        tempo = 1.0 / pitch_shift
        tempo_filters = _chain_atempo(tempo)
        af_parts.extend([
            "aformat=channel_layouts=stereo",
            f"asetrate={sample_rate}*{pitch_shift}",
            *tempo_filters,
            f"aresample={sample_rate}",
        ])
    af = ",".join(af_parts) if af_parts else None

    # If we have intro or outro, output the main part to a temp file
    needs_concat = intro_path or outro_path
    if needs_concat:
        main_output = os.path.join(temp_dir, "_main_processed.mp4")
    else:
        main_output = output_path

    cmd = [
        "ffmpeg", "-y",
    ]

    # Trim start (remove original intro)
    if trim_intro_sec > 0:
        cmd.extend(["-ss", str(trim_intro_sec)])

    # Trim end (remove promo content) — use -t for duration from -ss point
    if trim_end_at and trim_end_at > trim_intro_sec:
        keep_duration = trim_end_at - trim_intro_sec
        cmd.extend(["-t", str(keep_duration)])

    cmd.extend([
        "-i", input_path,
        "-i", watermark_path,
        "-filter_complex_script", filter_script,
        "-map", "[v_out]",
    ])

    if af:
        cmd.extend(["-map", "0:a", "-af", af, "-c:a", "aac", "-b:a", "192k"])
    else:
        cmd.extend(["-map", "0:a", "-c:a", "copy"])

    cmd.extend(["-c:v", "libx264", "-crf", "22", "-preset", "veryfast", "-threads", "1", main_output])

    print(f"  Command: {' '.join(cmd)}\n")
    _run_ffmpeg(cmd, "Processing")

    main_size = os.path.getsize(main_output) / (1024 * 1024)
    print(f"  Main video: {main_output} ({main_size:.1f} MB)")

    # =====================================================================
    # STEP 2: Prepare intro/outro and concatenate
    # =====================================================================
    if needs_concat:
        # Get main video's fps for matching
        fps_result = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "default=noprint_wrappers=1:nokey=1", main_output,
        ], capture_output=True, text=True)
        main_fps = fps_result.stdout.strip() or "25"

        ts_files = []
        temp_files = []

        # Prepare intro if provided
        if intro_path:
            print("\nSTEP 2a: Preparing your custom intro...")
            intro_prepared = os.path.join(temp_dir, "_intro_prepared.mp4")
            intro_cmd = [
                "ffmpeg", "-y", "-i", intro_path,
                "-vf", f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
                       f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black",
                "-c:v", "libx264", "-crf", "20", "-preset", "fast",
                "-c:a", "aac", "-b:a", "192k", "-ar", str(sample_rate), "-ac", "2",
                "-r", main_fps, intro_prepared,
            ]
            _run_ffmpeg(intro_cmd, "Intro prep")
            temp_files.append(intro_prepared)

            intro_ts = os.path.join(temp_dir, "_intro.ts")
            _run_ffmpeg([
                "ffmpeg", "-y", "-i", intro_prepared,
                "-c", "copy", "-bsf:v", "h264_mp4toannexb", "-f", "mpegts", intro_ts,
            ], "Intro TS")
            ts_files.append(intro_ts)
            temp_files.append(intro_ts)

        # Convert main to TS
        print("\n  Converting main video to TS...")
        main_ts = os.path.join(temp_dir, "_main.ts")
        _run_ffmpeg([
            "ffmpeg", "-y", "-i", main_output,
            "-c", "copy", "-bsf:v", "h264_mp4toannexb", "-f", "mpegts", main_ts,
        ], "Main TS")
        ts_files.append(main_ts)
        temp_files.append(main_ts)

        # Prepare outro if provided
        if outro_path:
            print("\nSTEP 2b: Preparing your subscription outro...")
            outro_prepared = os.path.join(temp_dir, "_outro_prepared.mp4")
            outro_cmd = [
                "ffmpeg", "-y", "-i", outro_path,
                "-vf", f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
                       f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black",
                "-c:v", "libx264", "-crf", "20", "-preset", "fast",
                "-c:a", "aac", "-b:a", "192k", "-ar", str(sample_rate), "-ac", "2",
                "-r", main_fps, outro_prepared,
            ]
            _run_ffmpeg(outro_cmd, "Outro prep")
            temp_files.append(outro_prepared)

            outro_ts = os.path.join(temp_dir, "_outro.ts")
            _run_ffmpeg([
                "ffmpeg", "-y", "-i", outro_prepared,
                "-c", "copy", "-bsf:v", "h264_mp4toannexb", "-f", "mpegts", outro_ts,
            ], "Outro TS")
            ts_files.append(outro_ts)
            temp_files.append(outro_ts)

        # =================================================================
        # STEP 3: Concatenate all parts using TS concat protocol
        # =================================================================
        parts_desc = []
        if intro_path:
            parts_desc.append("intro")
        parts_desc.append("main")
        if outro_path:
            parts_desc.append("outro")
        print(f"\nSTEP 3: Concatenating {' + '.join(parts_desc)}...")

        concat_input = "concat:" + "|".join(ts_files)
        concat_cmd = [
            "ffmpeg", "-y",
            "-i", concat_input,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            output_path,
        ]
        _run_ffmpeg(concat_cmd, "Concat")

        # Clean up all temp files
        temp_files.extend([main_output, filter_script])
        for tmp in temp_files:
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except OSError:
                pass

    # Clean up filter script if no concat needed
    if not needs_concat and os.path.isfile(filter_script):
        os.remove(filter_script)

    output_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print(f"DONE! Output: {output_path} ({output_size:.1f} MB)")
    print(f"{'=' * 60}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Remove ALL StudyIQ branding from video and replace with your own"
    )
    parser.add_argument("input", help="Input video path")
    parser.add_argument("-o", "--output", help="Output path (default: <input>_rebranded.mp4)")
    parser.add_argument("--watermark", default="assets/watermark.png",
                        help="Your watermark PNG path")
    parser.add_argument("--pitch", type=float, default=1.15,
                        help="Voice pitch shift (default: 1.15 = 15%% higher)")
    parser.add_argument("--text", default="Civil Services & Competitive Exam Prep",
                        help="Your branding text overlay")
    parser.add_argument("--intro", default=None,
                        help="Your custom intro video to prepend")
    parser.add_argument("--outro", default=None,
                        help="Your subscription/outro video to append at the end")
    parser.add_argument("--trim-intro", type=float, default=28.0,
                        help="Seconds of original intro to remove (default: 28)")
    parser.add_argument("--trim-end", type=float, default=None,
                        help="Cut video at this timestamp to remove end promo (e.g. 670)")
    parser.add_argument("--upscale-to", type=int, default=None,
                        help="Upscale output to this height (e.g. 720 for 720p)")

    args = parser.parse_args()

    if not args.output:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_rebranded{ext}"

    # Change to project root for relative paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)

    process_video_rebrand(
        input_path=args.input,
        output_path=args.output,
        watermark_path=args.watermark,
        pitch_shift=args.pitch,
        custom_text=args.text,
        intro_path=args.intro,
        outro_path=args.outro,
        trim_intro_sec=args.trim_intro,
        trim_end_at=args.trim_end,
        upscale_to=args.upscale_to,
    )


if __name__ == "__main__":
    main()
