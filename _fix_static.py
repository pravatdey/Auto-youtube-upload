"""Fix the 3 sections that have no motion and rebuild final video."""
import subprocess
import os
import json

env = os.environ.copy()
env["TEMP"] = "D:/temp"
env["TMP"] = "D:/temp"

os.chdir(os.path.dirname(os.path.abspath(__file__)))

TEMP_DIR = "D:/temp/news_video_temp"
FONT_PATH = "assets/fonts/arial.ttf"

with open(os.path.join(TEMP_DIR, "food_crisis_script.json"), "r", encoding="utf-8") as f:
    script = json.load(f)

fix_sections = [1, 10, 12]  # sections 2, 11, 13 (0-indexed)

for idx in fix_sections:
    img = os.path.join(TEMP_DIR, f"food_slide_{idx:02d}.png")
    audio = os.path.join(TEMP_DIR, f"food_narr_{idx:02d}.mp3")
    clip = os.path.join(TEMP_DIR, f"_cine_{idx:02d}.mp4")
    faded = os.path.join(TEMP_DIR, f"_cine_ts_{idx:02d}.mp4")

    r = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio,
    ], capture_output=True, text=True)
    dur = float(r.stdout.strip())
    frames = int(dur * 25)

    zoompan = (
        f"zoompan=z='min(zoom+0.0005,1.10)'"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s=1920x1080:fps=25"
    )

    kp = script["sections"][idx].get("key_points", [])[:4]
    font_file = FONT_PATH.replace("\\", "/")
    dt = []
    if len(kp) > 0 and dur > 8:
        interval = (dur - 8) / len(kp)
        for j, pt in enumerate(kp):
            t = 3 + j * interval
            safe = (pt.replace("'", "\u2019")
                      .replace(":", " -")
                      .replace("%", " pct")
                      .replace("\\", "")
                      .replace('"', ""))
            dt.append(
                f"drawtext=fontfile='{font_file}'"
                f":text='>>  {safe}'"
                f":fontcolor=white:fontsize=30"
                f":x=40:y={60 + j * 55}"
                f":box=1:boxcolor=black@0.6:boxborderw=10"
                f":enable='gte(t,{t:.1f})'"
            )

    vf = ",".join([zoompan, "format=yuv420p"] + dt)

    print(f"Fixing section {idx+1} ({dur:.0f}s)...")
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", img, "-i", audio,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-t", str(dur), clip,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    print(f"  Motion clip: {'OK' if r.returncode == 0 else 'FAIL'}")

    fade_vf = f"fade=t=in:st=0:d=0.8,fade=t=out:st={dur-0.8:.1f}:d=0.8"
    afade = f"afade=t=in:st=0:d=0.5,afade=t=out:st={dur-0.5:.1f}:d=0.5"
    subprocess.run([
        "ffmpeg", "-y", "-i", clip, "-vf", fade_vf, "-af", afade,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", faded,
    ], capture_output=True, text=True, env=env)
    print(f"  Faded clip: OK")

print("\nRebuilding final video...")

# Concat all 18
concat_file = os.path.join(TEMP_DIR, "_fix_concat.txt")
with open(concat_file, "w") as f:
    for i in range(18):
        ts = os.path.join(TEMP_DIR, f"_cine_ts_{i:02d}.mp4").replace("\\", "/")
        f.write(f"file '{ts}'\n")

concat_out = os.path.join(TEMP_DIR, "_fix_concat.mp4")
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", concat_file, "-c", "copy", concat_out,
], capture_output=True, text=True, env=env)

# Watermark
OUTPUT = "D:/temp/Global_Food_Crisis_Hormuz.mp4"
wm_w = int(1920 * 0.12)
subprocess.run([
    "ffmpeg", "-y", "-i", concat_out, "-i", "assets/watermark.png",
    "-filter_complex",
    f"[1:v]scale={wm_w}:-1,format=rgba,colorchannelmixer=aa=0.7[wm];"
    f"[0:v][wm]overlay=W-w-20:H-h-20[out]",
    "-map", "[out]", "-map", "0:a",
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
    "-c:a", "copy", OUTPUT,
], capture_output=True, text=True, env=env)

# Intro + outro
FINAL = "D:/temp/Global_Food_Crisis_Hormuz_FINAL.mp4"
parts = []
for j, src in enumerate(["D:/temp/channel_intro.mp4", OUTPUT, "D:/temp/channel_subscribe_outro.mp4"]):
    ts = f"D:/temp/_fix_part_{j}.ts"
    subprocess.run([
        "ffmpeg", "-y", "-i", src,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
               "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=25",
        "-f", "mpegts", ts,
    ], capture_output=True, text=True, env=env)
    parts.append(ts)

subprocess.run([
    "ffmpeg", "-y", "-i", "concat:" + "|".join(parts),
    "-c", "copy", "-bsf:a", "aac_adtstoasc", FINAL,
], capture_output=True, text=True, env=env)

for ts in parts:
    os.remove(ts)
for tmp in [concat_file, concat_out]:
    try:
        os.remove(tmp)
    except OSError:
        pass

size = os.path.getsize(FINAL) / (1024 * 1024)
r = subprocess.run([
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1", FINAL,
], capture_output=True, text=True)
dur = float(r.stdout.strip()) if r.stdout.strip() else 0

print(f"\nDONE! {FINAL}")
print(f"Duration: {dur:.0f}s ({dur/60:.1f} min)")
print(f"Size: {size:.1f} MB")
print("All 18 sections now have motion!")
