"""Fix sections 2 and 13 using crop-based motion instead of zoompan."""
import subprocess
import os
import json
from PIL import Image

os.chdir(os.path.dirname(os.path.abspath(__file__)))
env = os.environ.copy()
env["TEMP"] = "D:/temp"
env["TMP"] = "D:/temp"

TEMP = "D:/temp/news_video_temp"
FONT = "assets/fonts/arial.ttf".replace("\\", "/")

with open(os.path.join(TEMP, "food_crisis_script.json"), "r", encoding="utf-8") as f:
    script = json.load(f)

for idx in [1, 12]:
    img_path = os.path.join(TEMP, f"food_slide_{idx:02d}.png")
    upscaled = os.path.join(TEMP, f"_up2_{idx:02d}.png")
    audio = os.path.join(TEMP, f"food_narr_{idx:02d}.mp3")
    clip = os.path.join(TEMP, f"_cine_{idx:02d}.mp4")
    faded = os.path.join(TEMP, f"_cine_ts_{idx:02d}.mp4")

    # Upscale to 2400x1350
    img = Image.open(img_path).resize((2400, 1350), Image.LANCZOS)
    img.save(upscaled)

    r = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio,
    ], capture_output=True, text=True)
    dur = float(r.stdout.strip())

    # Use crop filter: pan from x=0 to x=480 over the duration
    # Speed = 480 pixels / (dur * 25 frames) = pixels per frame
    ppf = 480 / (dur * 25)
    crop_filter = f"crop=1920:1080:'min(n*{ppf:.4f},480)':0"

    # Key points
    kp = script["sections"][idx].get("key_points", [])[:4]
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
                f"drawtext=fontfile='{FONT}'"
                f":text='>>  {safe}'"
                f":fontcolor=white:fontsize=30"
                f":x=40:y={60 + j * 55}"
                f":box=1:boxcolor=black@0.6:boxborderw=10"
                f":enable='gte(t,{t:.1f})'"
            )

    vf = ",".join([crop_filter, "format=yuv420p"] + dt)

    print(f"Fixing section {idx+1} ({dur:.0f}s) with crop motion...")
    r = subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", upscaled, "-i", audio,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-t", str(dur), clip,
    ], capture_output=True, text=True, env=env)
    print(f"  Clip: {'OK' if r.returncode == 0 else 'FAIL'}")
    if r.returncode != 0:
        print(f"  ERR: {r.stderr[-200:]}")

    subprocess.run([
        "ffmpeg", "-y", "-i", clip,
        "-vf", f"fade=t=in:st=0:d=0.8,fade=t=out:st={dur-0.8:.1f}:d=0.8",
        "-af", f"afade=t=in:st=0:d=0.5,afade=t=out:st={dur-0.5:.1f}:d=0.5",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", faded,
    ], capture_output=True, text=True, env=env)
    print(f"  Faded: OK")
    os.remove(upscaled)

# Rebuild final
print("\nRebuilding final video...")
concat_f = os.path.join(TEMP, "_final2.txt")
with open(concat_f, "w") as f:
    for i in range(18):
        p = os.path.join(TEMP, f"_cine_ts_{i:02d}.mp4").replace("\\", "/")
        f.write(f"file '{p}'\n")

concat_out = os.path.join(TEMP, "_final2.mp4")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_f, "-c", "copy", concat_out],
               capture_output=True, text=True, env=env)

OUTPUT = "D:/temp/Global_Food_Crisis_Hormuz.mp4"
subprocess.run([
    "ffmpeg", "-y", "-i", concat_out, "-i", "assets/watermark.png",
    "-filter_complex",
    f"[1:v]scale={int(1920*0.12)}:-1,format=rgba,colorchannelmixer=aa=0.7[w];"
    f"[0:v][w]overlay=W-w-20:H-h-20[o]",
    "-map", "[o]", "-map", "0:a", "-c:v", "libx264", "-preset", "veryfast",
    "-crf", "23", "-c:a", "copy", OUTPUT,
], capture_output=True, text=True, env=env)

FINAL = "D:/temp/Global_Food_Crisis_Hormuz_FINAL.mp4"
parts = []
for j, src in enumerate(["D:/temp/channel_intro.mp4", OUTPUT, "D:/temp/channel_subscribe_outro.mp4"]):
    ts = f"D:/temp/_fx2_{j}.ts"
    subprocess.run([
        "ffmpeg", "-y", "-i", src, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
               "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=25",
        "-f", "mpegts", ts,
    ], capture_output=True, text=True, env=env)
    parts.append(ts)

subprocess.run(["ffmpeg", "-y", "-i", "concat:" + "|".join(parts),
                "-c", "copy", "-bsf:a", "aac_adtstoasc", FINAL],
               capture_output=True, text=True, env=env)
for ts in parts:
    os.remove(ts)
for tmp in [concat_f, concat_out]:
    try:
        os.remove(tmp)
    except OSError:
        pass

# Verify
import numpy as np
print("\nVerifying motion...")
for ts_check, name in [(94, "Sec 2"), (1117, "Sec 13")]:
    f1, f2 = "D:/temp/_v1.png", "D:/temp/_v2.png"
    subprocess.run(["ffmpeg", "-y", "-ss", str(ts_check+3), "-i", FINAL, "-frames:v", "1", f1],
                   capture_output=True, text=True, env=env)
    subprocess.run(["ffmpeg", "-y", "-ss", str(ts_check+5), "-i", FINAL, "-frames:v", "1", f2],
                   capture_output=True, text=True, env=env)
    i1 = np.array(Image.open(f1))
    i2 = np.array(Image.open(f2))
    diff = np.mean(np.abs(i1.astype(float) - i2.astype(float)))
    print(f"  {name}: diff={diff:.2f} -> {'MOTION OK' if diff > 1.0 else 'STATIC'}")
    os.remove(f1)
    os.remove(f2)

sz = os.path.getsize(FINAL) / (1024 * 1024)
print(f"\nFINAL: {FINAL} ({sz:.1f} MB)")
