# -*- coding: utf-8 -*-
"""
Build the "Cockroach Janta Party" Gen-Z explainer video.

Animated-graphics style (no real photos):
  - Moving gradient background + drifting particles
  - Animated heading reveal
  - Bullet points that pop in one-by-one, synced to narration length
  - Section progress bar + branding
Audio: Gemini-TTS Hindi clips from output/cjp_audio/.
Finally prepends the user's intro video.

Run AFTER cjp_generate_audio.py.
"""
import os
import sys
import json
import math
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from cjp_content import SECTIONS, VIDEO_TITLE, THUMBNAIL_LINE1, THUMBNAIL_LINE2, THUMBNAIL_SUB

# ---------------------------------------------------------------- paths
ROOT = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(ROOT, "output", "cjp_audio")
WORK_DIR = os.path.join("D:/temp", "cjp_video_work")
OUTPUT_DIR = os.path.join(ROOT, "output")
FINAL_NO_INTRO = os.path.join(WORK_DIR, "_cjp_no_intro.mp4")
FINAL_OUTPUT = os.path.join(OUTPUT_DIR, "Cockroach_Janta_Party_GenZ.mp4")
THUMBNAIL_OUTPUT = os.path.join(OUTPUT_DIR, "Cockroach_Janta_Party_GenZ_thumbnail.jpg")
INTRO_VIDEO = r"C:\Users\PravatkumarDey\Downloads\CivilPrepHub_this_is_cnaenl_na.mp4"

os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------- video config
W, H = 1920, 1080
FPS = 30
TARGET_TOTAL = 25 * 60          # 25 minutes target (excluding intro)

# ---------------------------------------------------------------- fonts
FONT_LATIN = "assets/fonts/arial.ttf"          # for big English headings
FONT_DEVA = r"C:\Windows\Fonts\Nirmala.ttc"    # Hindi (Devanagari)


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        return ImageFont.load_default()


F_TITLE = _font(FONT_LATIN, 92)
F_SUB = _font(FONT_DEVA, 52)
F_BULLET = _font(FONT_DEVA, 46)
F_SMALL = _font(FONT_DEVA, 30)
F_TAG = _font(FONT_LATIN, 30)
F_NUM = _font(FONT_LATIN, 200)

# ---------------------------------------------------------------- palette
# Per-section accent colours (dark teal/amber theme — "cockroach + neon" vibe)
ACCENTS = [
    (255, 196, 0),    # amber
    (0, 200, 180),    # teal
    (255, 110, 80),   # coral
    (130, 170, 255),  # blue
    (200, 130, 255),  # purple
    (255, 196, 0),
    (0, 200, 180),
    (255, 110, 80),
    (255, 90, 90),    # red (anger section)
    (90, 230, 140),   # green (benefits)
    (130, 170, 255),
    (255, 196, 0),
]
BG_TOP = (14, 18, 28)
BG_BOTTOM = (28, 22, 40)
TEXT_WHITE = (245, 245, 248)
TEXT_DIM = (170, 175, 190)
BRAND = "CivilPrepHub"


# ================================================================
# Background helpers
# ================================================================
def _gradient_bg(accent, t):
    """Animated diagonal gradient with a slowly-shifting accent glow."""
    img = Image.new("RGB", (W, H))
    px = img.load()
    # vertical base gradient
    for y in range(H):
        r = y / H
        cr = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * r)
        cg = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * r)
        cb = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * r)
        for x in range(0, W, 4):
            px[x, y] = (cr, cg, cb)
            if x + 1 < W: px[x + 1, y] = (cr, cg, cb)
            if x + 2 < W: px[x + 2, y] = (cr, cg, cb)
            if x + 3 < W: px[x + 3, y] = (cr, cg, cb)
    return img


def _radial_glow(accent, cx, cy, radius, strength):
    """Return an RGBA glow layer to composite over the background."""
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    steps = 28
    for i in range(steps, 0, -1):
        rr = int(radius * i / steps)
        a = int(strength * (1 - i / steps))
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  fill=(accent[0], accent[1], accent[2], a))
    return glow.filter(ImageFilter.GaussianBlur(40))


def _make_bg(accent, t, seed):
    """Composed animated background for a given normalised time t in [0,1)."""
    base = _gradient_bg(accent, t)
    # two drifting glows
    g1x = int(W * (0.22 + 0.10 * math.sin(t * 2 * math.pi + seed)))
    g1y = int(H * (0.30 + 0.08 * math.cos(t * 2 * math.pi * 0.7 + seed)))
    g2x = int(W * (0.80 + 0.08 * math.cos(t * 2 * math.pi * 0.9 + seed)))
    g2y = int(H * (0.72 + 0.07 * math.sin(t * 2 * math.pi * 0.6 + seed)))
    base = base.convert("RGBA")
    base = Image.alpha_composite(base, _radial_glow(accent, g1x, g1y, 620, 70))
    base = Image.alpha_composite(base, _radial_glow((90, 110, 160), g2x, g2y, 540, 55))

    # drifting particles
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(34):
        ph = (i * 0.137 + seed * 0.31) % 1.0
        px_ = (W * ((i * 0.0739 + t * (0.05 + 0.04 * (i % 3))) % 1.0))
        py_ = (H * ((ph + t * (0.03 + 0.02 * (i % 4))) % 1.0))
        sz = 2 + (i % 4)
        a = int(60 + 90 * (0.5 + 0.5 * math.sin(t * 2 * math.pi + i)))
        d.ellipse([px_ - sz, py_ - sz, px_ + sz, py_ + sz],
                  fill=(accent[0], accent[1], accent[2], a))
    base = Image.alpha_composite(base, layer)
    return base.convert("RGB")


# ================================================================
# Text helpers
# ================================================================
def _wrap(text, font, max_w, draw):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _text_shadow(draw, xy, text, font, fill, shadow=(0, 0, 0), off=3, anchor=None):
    x, y = xy
    draw.text((x + off, y + off), text, font=font, fill=shadow, anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


def _ease_out(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


# ================================================================
# Frame composition for a content section
# ================================================================
def compose_section_frame(section, idx, total, t_norm, frame_progress, accent):
    """
    t_norm        : 0..1 position within the section (for bg animation)
    frame_progress: 0..1 position within section (drives text reveals)
    """
    img = _make_bg(accent, t_norm, seed=idx * 1.7 + 0.5)
    draw = ImageDraw.Draw(img, "RGBA")

    margin = 110

    # ---- top tag bar
    tag = f"COCKROACH JANTA PARTY  ·  GEN-Z EXPLAINER"
    draw.rectangle([0, 0, W, 70], fill=(0, 0, 0, 130))
    draw.rectangle([0, 70, W, 74], fill=(accent[0], accent[1], accent[2], 255))
    _text_shadow(draw, (margin, 18), tag, F_TAG, accent)
    sec_lbl = f"SECTION {idx}/{total}"
    draw.text((W - margin, 18), sec_lbl, font=F_TAG, fill=TEXT_DIM, anchor="ra")

    # ---- big faint section number, top-right
    num_str = f"{idx:02d}"
    draw.text((W - 90, 150), num_str, font=F_NUM,
              fill=(accent[0], accent[1], accent[2], 28), anchor="ra")

    # ---- heading reveal (slides up + fades in over first 12% of section)
    head_p = _ease_out(frame_progress / 0.12)
    head_y = 210 + int((1 - head_p) * 40)
    head_alpha = int(255 * head_p)
    accent_a = (accent[0], accent[1], accent[2], head_alpha)
    white_a = (TEXT_WHITE[0], TEXT_WHITE[1], TEXT_WHITE[2], head_alpha)

    # accent kicker line above heading
    draw.rectangle([margin, head_y - 6, margin + int(150 * head_p), head_y - 1],
                   fill=accent_a)
    # English heading
    _text_shadow(draw, (margin, head_y + 10), section["title"], F_TITLE, accent_a)
    # Hindi subtitle
    sub_y = head_y + 10 + 110
    draw.text((margin, sub_y), section["subtitle"], font=F_SUB,
              fill=white_a)

    # divider under heading block
    div_y = sub_y + 90
    draw.rectangle([margin, div_y, margin + int((W - 2 * margin) * head_p), div_y + 3],
                   fill=(accent[0], accent[1], accent[2], int(160 * head_p)))

    # ---- bullets pop in one-by-one across the section
    bullets = section["bullets"]
    n = len(bullets)
    # reveal window: bullets appear between 15% and 80% of the section
    start_p, end_p = 0.15, 0.82
    by = div_y + 70
    for j, b in enumerate(bullets):
        appear = start_p + (end_p - start_p) * (j / max(1, n))
        bp = _ease_out((frame_progress - appear) / 0.10)
        if bp <= 0:
            by += 110
            continue
        b_alpha = int(255 * bp)
        slide = int((1 - bp) * 60)
        bx = margin + slide
        row_y = by

        # bullet chip (rounded marker)
        chip = 54
        draw.rounded_rectangle(
            [bx, row_y, bx + chip, row_y + chip], radius=14,
            fill=(accent[0], accent[1], accent[2], b_alpha))
        draw.text((bx + chip // 2, row_y + chip // 2 - 4), str(j + 1),
                  font=_font(FONT_LATIN, 34),
                  fill=(15, 18, 28, b_alpha), anchor="mm")

        # bullet text (may wrap)
        tx = bx + chip + 34
        lines = _wrap(b, F_BULLET, W - tx - margin, draw)
        ty = row_y + (chip - len(lines) * 52) // 2
        for ln in lines:
            draw.text((tx + 2, ty + 2), ln, font=F_BULLET, fill=(0, 0, 0, b_alpha))
            draw.text((tx, ty), ln, font=F_BULLET,
                      fill=(TEXT_WHITE[0], TEXT_WHITE[1], TEXT_WHITE[2], b_alpha))
            ty += 52
        by += max(110, len(lines) * 52 + 44)

    # ---- bottom progress bar (whole video) + branding
    draw.rectangle([0, H - 56, W, H], fill=(0, 0, 0, 150))
    overall = (idx - 1 + frame_progress) / total
    draw.rectangle([0, H - 56, int(W * overall), H - 52],
                   fill=(accent[0], accent[1], accent[2], 255))
    draw.text((margin, H - 44), BRAND, font=F_SMALL, fill=accent)
    draw.text((W - margin, H - 44), "Like  ·  Share  ·  Subscribe",
              font=F_SMALL, fill=TEXT_DIM, anchor="ra")

    return img


# ================================================================
# ffprobe helper
# ================================================================
def audio_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 30.0


# ================================================================
# Render one section -> mp4 (animated frames + its audio)
# ================================================================
def render_section(section, idx, total, accent, seg_duration):
    """Render a section as an mp4 with N animated frames stretched to seg_duration."""
    sec_dir = os.path.join(WORK_DIR, f"sec_{idx:02d}")
    if os.path.exists(sec_dir):
        shutil.rmtree(sec_dir)
    os.makedirs(sec_dir)

    # Number of distinct rendered frames. Reusing frames at a low keyframe rate
    # keeps render time sane; ffmpeg ramps it to FPS. ~1 frame / 0.5s of motion.
    n_frames = max(24, int(seg_duration * 2))
    n_frames = min(n_frames, 130)  # cap for very long sections

    for k in range(n_frames):
        prog = k / (n_frames - 1) if n_frames > 1 else 0.0
        frame = compose_section_frame(section, idx, total, prog, prog, accent)
        frame.save(os.path.join(sec_dir, f"f_{k:04d}.png"))

    seg_fps = n_frames / seg_duration  # input framerate so frames span the audio
    audio_path = os.path.join(AUDIO_DIR, f"{section['key']}.mp3")
    out_path = os.path.join(WORK_DIR, f"section_{idx:02d}.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", f"{seg_fps:.6f}",
        "-i", os.path.join(sec_dir, "f_%04d.png").replace("\\", "/"),
        "-i", audio_path.replace("\\", "/"),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-t", f"{seg_duration:.3f}",
        out_path,
    ]
    env = os.environ.copy()
    env["TEMP"] = "D:/temp"
    env["TMP"] = "D:/temp"
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print(f"   ERROR rendering section {idx}:\n{r.stderr[-600:]}")
        return None
    shutil.rmtree(sec_dir, ignore_errors=True)
    return out_path


# ================================================================
# Thumbnail
# ================================================================
def make_thumbnail():
    img = Image.new("RGB", (1280, 720))
    d = ImageDraw.Draw(img, "RGBA")
    # bg
    for y in range(720):
        r = y / 720
        d.line([(0, y), (1280, y)],
               fill=(int(16 + r * 20), int(18 + r * 8), int(30 + r * 22)))
    d_img = Image.alpha_composite(img.convert("RGBA"),
                                  _radial_glow((255, 196, 0), 300, 260, 520, 90)
                                  .resize((1280, 720)))
    img = d_img.convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    f1 = _font(FONT_LATIN, 130)
    f2 = _font(FONT_LATIN, 130)
    f3 = _font(FONT_DEVA, 56)
    f4 = _font(FONT_LATIN, 40)
    # side stripe
    d.rectangle([0, 0, 26, 720], fill=(255, 196, 0))
    _text_shadow(d, (70, 90), THUMBNAIL_LINE1, f1, (255, 196, 0), off=5)
    _text_shadow(d, (70, 230), THUMBNAIL_LINE2, f2, (245, 245, 248), off=5)
    d.rectangle([74, 390, 620, 400], fill=(0, 200, 180))
    _text_shadow(d, (70, 430), THUMBNAIL_SUB, f3, (0, 200, 180), off=3)
    # bottom brand bar
    d.rectangle([0, 640, 1280, 720], fill=(0, 0, 0, 200))
    d.text((70, 662), "CivilPrepHub  ·  Gen-Z Andolan Explained",
           font=f4, fill=(255, 220, 120))
    img.save(THUMBNAIL_OUTPUT, quality=95)
    print(f"  Thumbnail: {THUMBNAIL_OUTPUT}")


# ================================================================
# Main
# ================================================================
def main():
    os.chdir(ROOT)
    print("=" * 64)
    print("  COCKROACH JANTA PARTY - VIDEO BUILDER")
    print("=" * 64)

    # --- check audio
    missing = [s["key"] for s in SECTIONS
               if not (os.path.exists(os.path.join(AUDIO_DIR, f"{s['key']}.mp3"))
                       and os.path.getsize(os.path.join(AUDIO_DIR, f"{s['key']}.mp3")) > 1000)]
    if missing:
        print(f"ERROR: {len(missing)} audio clip(s) missing: {missing}")
        print("Run:  python cjp_generate_audio.py")
        sys.exit(1)

    # --- compute per-section durations
    # base = narration length + padding; then scale all to hit 25 min target.
    PAD = 1.6
    base = []
    for s in SECTIONS:
        d = audio_duration(os.path.join(AUDIO_DIR, f"{s['key']}.mp3"))
        base.append(d + PAD)
    raw_total = sum(base)
    scale = TARGET_TOTAL / raw_total if raw_total > 0 else 1.0
    # never compress audio below its real length: only stretch the tail (silence)
    durations = [max(base[i], base[i] * scale) for i in range(len(base))]
    planned = sum(durations)
    print(f"  Narration total: {raw_total/60:.1f} min  ->  planned video: {planned/60:.1f} min")
    print(f"  ({len(SECTIONS)} sections)\n")

    # --- render each section
    section_videos = []
    for i, s in enumerate(SECTIONS):
        idx = i + 1
        accent = ACCENTS[i % len(ACCENTS)]
        print(f"  [{idx}/{len(SECTIONS)}] Rendering '{s['title']}' "
              f"({durations[i]:.1f}s)...")
        out = render_section(s, idx, len(SECTIONS), accent, durations[i])
        if out:
            section_videos.append(out)
        else:
            print(f"  WARNING: section {idx} failed, skipping.")

    if not section_videos:
        print("ERROR: no sections rendered.")
        sys.exit(1)

    env = os.environ.copy()
    env["TEMP"] = "D:/temp"
    env["TMP"] = "D:/temp"

    # --- concat sections (re-encode safe; uniform params already)
    print("\n  Concatenating sections...")
    concat_list = os.path.join(WORK_DIR, "_sections.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for v in section_videos:
            f.write(f"file '{v.replace(chr(92), '/')}'\n")
    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c", "copy", FINAL_NO_INTRO],
        capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print("  concat -c copy failed, re-encoding...")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             FINAL_NO_INTRO],
            capture_output=True, text=True, env=env, check=True)

    # --- prepend the user's intro video (normalised to 1920x1080/30fps/48k stereo)
    print("  Prepending intro video...")
    intro_norm = os.path.join(WORK_DIR, "_intro_norm.mp4")
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", INTRO_VIDEO,
         "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps={FPS}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         intro_norm],
        capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print(f"  Intro normalise failed:\n{r.stderr[-600:]}")
        print("  Using video without intro.")
        shutil.copy2(FINAL_NO_INTRO, FINAL_OUTPUT)
    else:
        final_list = os.path.join(WORK_DIR, "_final.txt")
        with open(final_list, "w", encoding="utf-8") as f:
            f.write(f"file '{intro_norm.replace(chr(92), '/')}'\n")
            f.write(f"file '{FINAL_NO_INTRO.replace(chr(92), '/')}'\n")
        r = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", final_list,
             "-c", "copy", FINAL_OUTPUT],
            capture_output=True, text=True, env=env)
        if r.returncode != 0:
            print("  Final concat -c copy failed, re-encoding...")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", final_list,
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                 "-pix_fmt", "yuv420p", "-r", str(FPS),
                 "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                 FINAL_OUTPUT],
                capture_output=True, text=True, env=env, check=True)

    # --- thumbnail
    make_thumbnail()

    # --- metadata for upload step
    final_dur = audio_duration(FINAL_OUTPUT)
    size_mb = os.path.getsize(FINAL_OUTPUT) / (1024 * 1024)
    metadata = {
        "video_path": FINAL_OUTPUT,
        "thumbnail_path": THUMBNAIL_OUTPUT,
        "title": VIDEO_TITLE,
        "description": (
            "Cockroach Janta Party kya hai? Gen-Z ka yeh viral digital andolan "
            "kaise shuru hua, iske peechhe kaun hai, iski maangein kya hain aur "
            "isse yuvaon ko kya fayda hai - is video mein poori jaankari Hindi mein.\n\n"
            "Is video mein cover kiya gaya:\n"
            "- Andolan ki shuruaat aur Supreme Court ki tippani\n"
            "- Sansthapak Abhijeet Dipke\n"
            "- Party ka manifesto aur pramukh maangein\n"
            "- Gen-Z ka gussa - berozgari aur mehngai\n"
            "- Is andolan ke fayde aur civic engagement\n\n"
            "Educational / current-affairs explainer. Sources: Al Jazeera, "
            "The Print, Sunday Guardian, DNA India.\n\n"
            "#CockroachJantaParty #GenZ #CurrentAffairs #UPSC #India"
        ),
        "tags": [
            "Cockroach Janta Party", "Cockroach Janta Party explained",
            "Gen Z movement India", "Abhijeet Dipke", "CJP",
            "current affairs", "UPSC current affairs", "youth unemployment India",
            "Gen Z politics", "viral movement India", "Hindi explainer",
            "civic engagement", "competitive exam", "India news",
        ],
        "category_id": "27",
        "privacy": "public",
        "duration_sec": final_dur,
    }
    meta_path = FINAL_OUTPUT.replace(".mp4", "_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 64)
    print("  VIDEO CREATED")
    print("=" * 64)
    print(f"  File      : {FINAL_OUTPUT}")
    print(f"  Size      : {size_mb:.1f} MB")
    print(f"  Duration  : {int(final_dur)//60}m {int(final_dur)%60}s "
          f"(incl. intro)")
    print(f"  Thumbnail : {THUMBNAIL_OUTPUT}")
    print(f"  Metadata  : {meta_path}")
    print("=" * 64)
    print("  Review the video. When approved, say 'upload' to publish to YouTube.")


if __name__ == "__main__":
    main()
