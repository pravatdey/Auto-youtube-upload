"""Prepend the channel intro clip to a generated video.

Re-encodes via the concat filter so the two clips join cleanly even if their
fps / audio params differ slightly. Output is <name>_final.mp4.

Usage:
    python prepend_intro.py <main_video.mp4> [intro.mp4]
"""

import os
import subprocess
import sys

DEFAULT_INTRO = "D:/temp/channel_intro.mp4"
W, H, FPS = 1920, 1080, 30


def run(cmd):
    env = os.environ.copy()
    env["TEMP"] = "D:/temp"
    env["TMP"] = "D:/temp"
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def main():
    if len(sys.argv) < 2:
        print("Usage: python prepend_intro.py <main_video.mp4> [intro.mp4]")
        sys.exit(1)

    main_video = sys.argv[1]
    intro = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_INTRO

    for p in (main_video, intro):
        if not os.path.isfile(p):
            print(f"ERROR: file not found: {p}")
            sys.exit(1)

    out = os.path.splitext(main_video)[0] + "_final.mp4"

    # Normalize both inputs to identical specs, then concat. Scale+pad keeps
    # aspect ratio; SAR reset and fps lock prevent concat mismatches.
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS},format=yuv420p"
    )
    filter_complex = (
        f"[0:v]{vf}[v0];[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];"
        f"[1:v]{vf}[v1];[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];"
        f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", intro,
        "-i", main_video,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        out,
    ]

    print(f"Prepending intro:\n  intro: {intro}\n  main:  {main_video}\n  out:   {out}")
    r = run(cmd)
    if r.returncode != 0:
        print("FFmpeg failed:\n", r.stderr[-1500:])
        sys.exit(1)

    size_mb = os.path.getsize(out) / (1024 * 1024)
    print(f"\nDONE -> {out} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
