"""Run rebrand on 7 parts of Indian Geography at 720p, sequentially."""
import subprocess
import sys
import os
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

INPUT = "C:/Users/PravatkumarDey/Downloads/videoplayback (1).mp4"
INTRO = "C:/Users/PravatkumarDey/Downloads/Intro_Video_Creation_Request.mp4"
OUTRO = "D:/temp/channel_subscribe_outro.mp4"
WATERMARK = "assets/watermark.png"
OUTPUT_DIR = "D:/temp"

PARTS = [
    (8, 3212),
    (3212, 6414),
    (6414, 9616),
    (9616, 12818),
    (12818, 16020),
    (16020, 19222),
    (19222, 22430),
]

total_start = time.time()

for i, (start, end) in enumerate(PARTS, 1):
    output = f"{OUTPUT_DIR}/Indian_Geography_Part{i}.mp4"

    # Skip already completed parts
    if os.path.isfile(output) and os.path.getsize(output) > 100 * 1024 * 1024:
        size = os.path.getsize(output) / (1024 * 1024)
        print(f"\n  SKIP Part {i}: already exists ({size:.0f} MB)")
        continue

    print(f"\n{'='*60}")
    print(f"  PART {i}/7: {start}s to {end}s ({(end-start)/60:.0f} min)")
    print(f"  Output: {output}")
    print(f"{'='*60}\n")

    cmd = [
        sys.executable, "-m", "pipeline.rebrand",
        INPUT,
        "-o", output,
        "--watermark", WATERMARK,
        "--pitch", "1.20",
        "--text", "Civil Services and Competitive Exam Prep",
        "--intro", INTRO,
        "--outro", OUTRO,
        "--trim-intro", str(start),
        "--trim-end", str(end),
        # No upscale — native 360p to avoid FFmpeg OOM crashes
    ]

    part_start = time.time()
    result = subprocess.run(cmd, capture_output=False)
    part_elapsed = time.time() - part_start

    if result.returncode != 0:
        print(f"\n  ERROR: Part {i} failed! (exit code {result.returncode})")
    else:
        size = os.path.getsize(output) / (1024 * 1024)
        print(f"\n  Part {i} done in {part_elapsed/60:.1f} min ({size:.0f} MB)")

total_elapsed = time.time() - total_start
print(f"\n{'='*60}")
print(f"  ALL 7 PARTS COMPLETE in {total_elapsed/60:.0f} minutes")
print(f"{'='*60}")

for i in range(1, 8):
    f = f"{OUTPUT_DIR}/Indian_Geography_Part{i}.mp4"
    if os.path.isfile(f):
        size = os.path.getsize(f) / (1024 * 1024)
        print(f"  Part {i}: {size:.0f} MB")
