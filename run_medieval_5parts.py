"""Run rebrand on 5 parts of Medieval Indian History at 720p, sequentially."""
import subprocess
import sys
import os
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

INPUT = "C:/Users/PravatkumarDey/Downloads/videoplayback.mp4"
INTRO = "C:/Users/PravatkumarDey/Downloads/Intro_Video_Creation_Request.mp4"
OUTRO = "C:/Users/PravatkumarDey/Downloads/Video_Subscription_for_Second_Content.mp4"
WATERMARK = "assets/watermark.png"
OUTPUT_DIR = "D:/temp"

# 5-part split points (from 70s to 14955s)
PARTS = [
    (70, 3047),
    (3047, 6024),
    (6024, 9001),
    (9001, 11978),
    (11978, 14955),
]

total_start = time.time()

for i, (start, end) in enumerate(PARTS, 1):
    output = f"{OUTPUT_DIR}/Medieval_Indian_History_Part{i}.mp4"

    print(f"\n{'='*60}")
    print(f"  PART {i}/5: {start}s to {end}s ({(end-start)/60:.0f} min)")
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
        "--upscale-to", "720",
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
print(f"  ALL 5 PARTS COMPLETE in {total_elapsed/60:.0f} minutes")
print(f"{'='*60}")

for i in range(1, 6):
    f = f"{OUTPUT_DIR}/Medieval_Indian_History_Part{i}.mp4"
    if os.path.isfile(f):
        size = os.path.getsize(f) / (1024 * 1024)
        print(f"  Part {i}: {size:.0f} MB")
