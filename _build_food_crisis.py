"""Build the Global Food Crisis video from the generated script."""
import json
import os
import sys
import asyncio
import subprocess
import re
import textwrap
import time
from io import BytesIO

import edge_tts
import requests
from PIL import Image, ImageDraw, ImageFont

# Config
TEMP_DIR = "D:/temp/news_video_temp"
FONT_PATH = "assets/fonts/arial.ttf"
WATERMARK = "assets/watermark.png"
VOICE = "en-IN-NeerjaNeural"
WIDTH, HEIGHT = 1920, 1080
OUTPUT = "D:/temp/Global_Food_Crisis_Hormuz.mp4"
FINAL = "D:/temp/Global_Food_Crisis_Hormuz_FINAL.mp4"
INTRO = "D:/temp/channel_intro.mp4"
OUTRO = "D:/temp/channel_subscribe_outro.mp4"

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(TEMP_DIR, exist_ok=True)

with open(os.path.join(TEMP_DIR, "food_crisis_script.json"), "r", encoding="utf-8") as f:
    script = json.load(f)

sections = script["sections"]
print(f"Sections: {len(sections)}")

env = os.environ.copy()
env["TEMP"] = "D:/temp"
env["TMP"] = "D:/temp"


# ===== STEP 1: TTS =====
print("\n[STEP 1] Generating narration...")
audio_files = []
for i, s in enumerate(sections):
    audio_path = os.path.join(TEMP_DIR, f"food_narr_{i:02d}.mp3")
    print(f"  [{i+1}/{len(sections)}] {s['heading'][:50]}...")
    communicate = edge_tts.Communicate(s["narration"], VOICE, rate="-10%")
    asyncio.run(communicate.save(audio_path))
    if os.path.isfile(audio_path) and os.path.getsize(audio_path) > 0:
        audio_files.append(audio_path)
print(f"  Generated {len(audio_files)} audio files")


# ===== STEP 2: Images =====
print("\n[STEP 2] Downloading images...")


def search_bing(query, limit=5):
    from urllib.parse import quote
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    url = f"https://www.bing.com/images/search?q={quote(query)}&form=HDRSC2&first=1"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return []
        pattern = r'murl&quot;:&quot;(https?://[^&]+?)&quot;'
        matches = re.findall(pattern, r.text)
        urls = [m for m in matches if any(ext in m.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"])]
        return urls[:limit]
    except Exception:
        return []


def download_img(url, path):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, timeout=15, headers=headers)
        if r.status_code != 200 or len(r.content) < 5000:
            return False
        img = Image.open(BytesIO(r.content)).convert("RGB")
        ratio = img.width / img.height
        target = WIDTH / HEIGHT
        if ratio > target:
            new_h, new_w = HEIGHT, int(HEIGHT * ratio)
        else:
            new_w, new_h = WIDTH, int(WIDTH / ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - WIDTH) // 2
        top = (new_h - HEIGHT) // 2
        img = img.crop((left, top, left + WIDTH, top + HEIGHT))
        img.save(path, quality=95)
        return True
    except Exception:
        return False


image_files = []
used = set()
for i, s in enumerate(sections):
    img_path = os.path.join(TEMP_DIR, f"food_slide_{i:02d}.png")
    query = s.get("image_search_query", s["heading"])
    print(f"  [{i+1}/{len(sections)}] {query[:50]}...")

    downloaded = False
    for url in search_bing(query):
        if url in used:
            continue
        if download_img(url, img_path):
            used.add(url)
            downloaded = True
            print(f"    [OK] Downloaded")
            break

    if not downloaded:
        alt = " ".join(query.split()[:3])
        for url in search_bing(alt, 3):
            if url in used:
                continue
            if download_img(url, img_path):
                used.add(url)
                downloaded = True
                print(f"    [OK] Downloaded (alt)")
                break

    if not downloaded:
        colors = [(0, 51, 102), (102, 0, 51), (0, 102, 51), (51, 51, 102),
                  (102, 51, 0), (0, 76, 102), (76, 0, 102), (102, 76, 0), (0, 80, 80)]
        c = colors[i % len(colors)]
        img = Image.new("RGB", (WIDTH, HEIGHT))
        draw = ImageDraw.Draw(img)
        for y in range(HEIGHT):
            cr = int(c[0] * (1 - y / HEIGHT * 0.5))
            cg = int(c[1] * (1 - y / HEIGHT * 0.5))
            cb = int(c[2] * (1 - y / HEIGHT * 0.5))
            draw.line([(0, y), (WIDTH, y)], fill=(cr, cg, cb))
        img.save(img_path)
        print(f"    [FALLBACK] Created slide")

    # Add bottom heading bar overlay
    if downloaded:
        img = Image.open(img_path).convert("RGB")
        try:
            fh = ImageFont.truetype(FONT_PATH, 42)
            fs = ImageFont.truetype(FONT_PATH, 20)
        except (OSError, IOError):
            fh = fs = ImageFont.load_default()

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        bar_h = 120
        bar_y = HEIGHT - bar_h
        for y in range(bar_h):
            alpha = int(200 * (y / bar_h))
            od.line([(0, bar_y + y), (WIDTH, bar_y + y)], fill=(0, 0, 0, alpha))
        od.rectangle([0, bar_y, WIDTH, bar_y + 3], fill=(255, 200, 0, 200))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        heading = s["heading"] if len(s["heading"]) <= 55 else s["heading"][:52] + "..."
        draw.text((42, HEIGHT - 75 + 2), heading, fill=(0, 0, 0), font=fh)
        draw.text((40, HEIGHT - 75), heading, fill=(255, 255, 255), font=fh)
        draw.text((WIDTH - 140, HEIGHT - 35), f"{i+1} / {len(sections)}", fill=(180, 180, 180), font=fs)
        img.save(img_path, quality=95)

    image_files.append(img_path)

print(f"  Created {len(image_files)} slides")


# ===== STEP 3: Assemble =====
print("\n[STEP 3] Assembling video with text overlays...")


def get_dur(p):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", p],
        capture_output=True, text=True
    )
    return float(r.stdout.strip()) if r.stdout.strip() else 30.0


section_vids = []
total_dur = 0
num = min(len(image_files), len(audio_files))

for i in range(num):
    sv = os.path.join(TEMP_DIR, f"_food_sec_{i:02d}.mp4")
    dur = get_dur(audio_files[i])
    total_dur += dur

    kp = sections[i].get("key_points", [])[:4]
    font_file = FONT_PATH.replace("\\", "/")
    dt = []
    if len(kp) > 0 and dur > 8:
        interval = (dur - 8) / len(kp)
        for j, pt in enumerate(kp):
            t = 3 + j * interval
            safe = (pt.replace("'", "\u2019")
                      .replace(":", " -")
                      .replace("%", " percent")
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

    vf = ",".join(["format=yuv420p"] + dt)
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_files[i],
        "-i", audio_files[i], "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-t", str(dur), sv,
    ]

    print(f"    [{i+1}/{num}] {dur:.0f}s - {sections[i]['heading'][:40]}...")
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        cmd2 = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_files[i],
            "-i", audio_files[i], "-vf", "format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-t", str(dur), sv,
        ]
        subprocess.run(cmd2, capture_output=True, text=True, env=env)
    section_vids.append(sv)

print(f"  Total: {total_dur:.0f}s ({total_dur/60:.1f} min)")

# Concat
concat_f = os.path.join(TEMP_DIR, "_food_concat.txt")
with open(concat_f, "w") as f:
    for sv in section_vids:
        f.write(f"file '{sv.replace(chr(92), '/')}'\n")

concat_out = os.path.join(TEMP_DIR, "_food_concat.mp4")
print("  Concatenating...")
subprocess.run(
    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_f, "-c", "copy", concat_out],
    capture_output=True, text=True, env=env,
)

# Add watermark
if os.path.isfile(WATERMARK):
    print("  Adding watermark...")
    wm_w = int(WIDTH * 0.12)
    r = subprocess.run([
        "ffmpeg", "-y", "-i", concat_out, "-i", WATERMARK,
        "-filter_complex",
        f"[1:v]scale={wm_w}:-1,format=rgba,colorchannelmixer=aa=0.7[wm];"
        f"[0:v][wm]overlay=W-w-20:H-h-20[out]",
        "-map", "[out]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "copy", OUTPUT,
    ], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        import shutil
        shutil.copy2(concat_out, OUTPUT)
else:
    import shutil
    shutil.copy2(concat_out, OUTPUT)

# Cleanup
for sv in section_vids:
    try:
        os.remove(sv)
    except OSError:
        pass
for tmp in [concat_f, concat_out]:
    try:
        os.remove(tmp)
    except OSError:
        pass

size = os.path.getsize(OUTPUT) / (1024 * 1024)
print(f"\n  Main video: {OUTPUT} ({size:.1f} MB)")


# ===== STEP 4: Add Intro + Outro =====
print("\n[STEP 4] Adding intro + outro...")
parts = []
for j, src in enumerate([INTRO, OUTPUT, OUTRO]):
    ts = f"D:/temp/_food_part_{j}.ts"
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

final_size = os.path.getsize(FINAL) / (1024 * 1024)
r = subprocess.run([
    "ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1", FINAL,
], capture_output=True, text=True)
final_dur = float(r.stdout.strip()) if r.stdout.strip() else 0


# ===== STEP 5: Thumbnail =====
print("\n[STEP 5] Creating thumbnail...")
thumb_path = "D:/temp/Global_Food_Crisis_Hormuz_thumbnail.jpg"
img = Image.new("RGB", (1280, 720))
draw = ImageDraw.Draw(img)
for y in range(720):
    ratio = y / 720
    r = int(100 * (1 - ratio))
    g = int(20)
    b = int(20 + ratio * 40)
    draw.line([(0, y), (1280, y)], fill=(r, g, b))

try:
    fb = ImageFont.truetype(FONT_PATH, 72)
    fm = ImageFont.truetype(FONT_PATH, 48)
    fs = ImageFont.truetype(FONT_PATH, 36)
except (OSError, IOError):
    fb = fm = fs = ImageFont.load_default()

draw.text((82, 82), "GLOBAL FOOD", fill=(0, 0, 0), font=fb)
draw.text((80, 80), "GLOBAL FOOD", fill=(255, 50, 50), font=fb)
draw.text((82, 182), "CRISIS", fill=(0, 0, 0), font=fb)
draw.text((80, 180), "CRISIS", fill=(255, 220, 0), font=fb)
draw.rectangle([80, 280, 600, 285], fill=(255, 220, 0))
draw.text((82, 302), "Strait of Hormuz", fill=(0, 0, 0), font=fm)
draw.text((80, 300), "Strait of Hormuz", fill=(255, 255, 255), font=fm)
draw.text((82, 372), "Fertilizer & Food Security", fill=(0, 0, 0), font=fs)
draw.text((80, 370), "Fertilizer & Food Security", fill=(200, 200, 220), font=fs)
draw.rectangle([0, 660, 1280, 720], fill=(0, 0, 0))
draw.text((50, 670), "Civil Services & Competitive Exam Prep", fill=(255, 220, 100), font=fs)

try:
    if os.path.isfile(WATERMARK):
        wm = Image.open(WATERMARK).convert("RGBA")
        wm = wm.resize((150, 150), Image.LANCZOS)
        img.paste(wm, (1280 - 200, 50), wm)
except Exception:
    pass

img.save(thumb_path, quality=95)

# Save metadata
meta = {
    "video_path": FINAL,
    "thumbnail_path": thumb_path,
    "title": script["title"],
    "description": script["description"],
    "tags": script["tags"],
    "category_id": "27",
    "privacy": "public",
}
with open("D:/temp/Global_Food_Crisis_Hormuz_metadata.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

print(f"\n{'=' * 60}")
print(f"  VIDEO CREATED SUCCESSFULLY!")
print(f"{'=' * 60}")
print(f"  Video:     {FINAL}")
print(f"  Duration:  {final_dur:.0f}s ({final_dur/60:.1f} min)")
print(f"  Size:      {final_size:.1f} MB")
print(f"  Thumbnail: {thumb_path}")
print(f"  Metadata:  D:/temp/Global_Food_Crisis_Hormuz_metadata.json")
print(f"{'=' * 60}")
