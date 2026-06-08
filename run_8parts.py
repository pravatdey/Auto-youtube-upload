"""Run rebrand on 8 parts of Modern Indian History sequentially."""
import subprocess
import sys
import os
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

INPUT = "C:/Users/PravatkumarDey/Downloads/Complete Modern Indian History.mp4"
INTRO = "C:/Users/PravatkumarDey/Downloads/Intro_Video_Creation_Request.mp4"
OUTRO = "C:/Users/PravatkumarDey/Downloads/Video_Subscription_for_Second_Clip.mp4"
WATERMARK = "assets/watermark.png"
OUTPUT_DIR = "D:/temp"

# 8-part split points (from 48s to 47098s)
PARTS = [
    (48, 5929),
    (5929, 11810),
    (11810, 17691),
    (17691, 23572),
    (23572, 29453),
    (29453, 35334),
    (35334, 41215),
    (41215, 47098),
]

total_start = time.time()

for i, (start, end) in enumerate(PARTS, 1):
    output = f"{OUTPUT_DIR}/Modern_Indian_History_Part{i}.mp4"
    log = f"{OUTPUT_DIR}/log_part{i}.txt"

    print(f"\n{'='*60}")
    print(f"  PART {i}/8: {start}s to {end}s ({(end-start)/3600:.1f}h)")
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
print(f"  ALL 8 PARTS COMPLETE in {total_elapsed/60:.0f} minutes")
print(f"{'='*60}")

# List all output files
for i in range(1, 9):
    f = f"{OUTPUT_DIR}/Modern_Indian_History_Part{i}.mp4"
    if os.path.isfile(f):
        size = os.path.getsize(f) / (1024 * 1024)
        print(f"  Part {i}: {size:.0f} MB")
