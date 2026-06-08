"""Build UPSC Prelims 2026 GS Paper 1 explainer video.

Pipeline:
  1. Load questions.json
  2. Render one PNG per question (1920x1080) — question text + 4 options +
     correct answer highlighted in green + one-line reason.
  3. Generate English TTS narration per question with edge-tts.
  4. Render intro and outro slides + TTS.
  5. Assemble final MP4 with ffmpeg using the per-slide audio durations.

Run:
    python build_video.py            # full build
    python build_video.py --slides   # only re-render slides
    python build_video.py --audio    # only re-generate audio
    python build_video.py --assemble # only re-assemble final MP4
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parent
QUESTIONS_FILE = ROOT / "questions.json"

OUT_DIR = Path("D:/temp/upsc_2026_video")
SLIDES_DIR = OUT_DIR / "slides"
AUDIO_DIR = OUT_DIR / "audio"
FINAL_VIDEO = OUT_DIR / "UPSC_Prelims_2026_GS1_AnswerKey.mp4"

W, H = 1920, 1080
FONT_PATH = str(REPO_ROOT / "assets/fonts/arial.ttf")
WATERMARK = REPO_ROOT / "assets/watermark.png"

VOICE = "en-IN-NeerjaNeural"  # Indian English female, clear and exam-coaching friendly
VOICE_RATE = "+5%"             # slightly faster for snappy 25-min target

# Colours (RGB)
BG_TOP = (15, 23, 42)        # deep navy
BG_BOTTOM = (30, 41, 59)     # slate
ACCENT = (250, 204, 21)      # amber (UPSC gold)
TEXT = (248, 250, 252)
SUBTLE = (148, 163, 184)
CORRECT_BG = (16, 185, 129)  # emerald
CORRECT_TEXT = (255, 255, 255)
OPTION_BG = (51, 65, 85)
REASON_BG = (30, 64, 175)    # blue


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------
def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size)


def wrap_text(text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels using the given font."""
    words = text.split()
    if not words:
        return [""]
    lines = []
    cur = words[0]
    for w in words[1:]:
        trial = cur + " " + w
        if fnt.getbbox(trial)[2] <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def draw_gradient_bg(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def draw_rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill, outline=None, width: int = 0) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


# ---------------------------------------------------------------------------
# Slide rendering
# ---------------------------------------------------------------------------
def render_intro_slide(path: Path) -> None:
    img = Image.new("RGB", (W, H))
    draw_gradient_bg(img)
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([(0, 0), (W, 12)], fill=ACCENT)

    # Title
    title_font = font(110)
    sub_font = font(56)
    small_font = font(40)

    title = "UPSC Prelims 2026"
    paper = "GS Paper 1 — Complete Answer Key"
    date = "Exam Date: 24 May 2026  |  Set D  |  100 Questions"
    cta = "Question by Question with Explanation"

    def cx(text, fnt):
        bbox = fnt.getbbox(text)
        return (W - (bbox[2] - bbox[0])) // 2

    draw.text((cx(title, title_font), 280), title, font=title_font, fill=TEXT)
    draw.text((cx(paper, sub_font), 430), paper, font=sub_font, fill=ACCENT)
    draw.text((cx(cta, sub_font), 530), cta, font=sub_font, fill=TEXT)
    draw.text((cx(date, small_font), 700), date, font=small_font, fill=SUBTLE)

    # Bottom accent bar
    draw.rectangle([(0, H - 12), (W, H)], fill=ACCENT)
    img.save(path, quality=95)


def render_outro_slide(path: Path) -> None:
    img = Image.new("RGB", (W, H))
    draw_gradient_bg(img)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (W, 12)], fill=ACCENT)
    draw.rectangle([(0, H - 12), (W, H)], fill=ACCENT)

    title_font = font(110)
    sub_font = font(60)
    small_font = font(44)

    title = "All the Best!"
    sub = "Like, Share & Subscribe"
    note = "Official UPSC answer key will be released soon"
    note2 = "Some answers may change — refer to the latest official key"

    def cx(text, fnt):
        bbox = fnt.getbbox(text)
        return (W - (bbox[2] - bbox[0])) // 2

    draw.text((cx(title, title_font), 300), title, font=title_font, fill=ACCENT)
    draw.text((cx(sub, sub_font), 470), sub, font=sub_font, fill=TEXT)
    draw.text((cx(note, small_font), 650), note, font=small_font, fill=SUBTLE)
    draw.text((cx(note2, small_font), 720), note2, font=small_font, fill=SUBTLE)
    img.save(path, quality=95)


def render_question_slide(q: dict, path: Path) -> None:
    img = Image.new("RGB", (W, H))
    draw_gradient_bg(img)
    draw = ImageDraw.Draw(img)

    # Accent bars
    draw.rectangle([(0, 0), (W, 8)], fill=ACCENT)
    draw.rectangle([(0, H - 8), (W, H)], fill=ACCENT)

    # Header row: "Q12 / 100" left, topic chip right
    h_font = font(44)
    q_label = f"Q{q['q']} / 100"
    draw.text((60, 40), q_label, font=h_font, fill=ACCENT)

    topic = q.get("topic", "")
    topic_font = font(34)
    tw = topic_font.getbbox(topic)[2]
    draw.rounded_rectangle(
        [(W - 60 - tw - 40, 40), (W - 60, 100)],
        radius=18, fill=OPTION_BG,
    )
    draw.text((W - 60 - tw - 20, 50), topic, font=topic_font, fill=TEXT)

    # Question text
    q_font = font(46)
    q_lines = wrap_text(q["question"], q_font, W - 160)
    y = 140
    for line in q_lines[:4]:  # cap at 4 lines so options always fit
        draw.text((80, y), line, font=q_font, fill=TEXT)
        y += 58

    y += 20  # gap before options
    options_top = y

    # Options grid: 2x2
    opt_font = font(40)
    opt_label_font = font(40)
    correct = q["answer"].lower()
    opts = q["options"]

    col_w = (W - 160 - 40) // 2  # two columns with 40px gutter
    row_h = 150

    positions = {
        "a": (80, options_top),
        "b": (80 + col_w + 40, options_top),
        "c": (80, options_top + row_h + 30),
        "d": (80 + col_w + 40, options_top + row_h + 30),
    }

    for key, (x, oy) in positions.items():
        is_correct = (key == correct)
        bg = CORRECT_BG if is_correct else OPTION_BG
        draw.rounded_rectangle([(x, oy), (x + col_w, oy + row_h)], radius=20, fill=bg)

        label = f"({key.upper()})"
        draw.text((x + 22, oy + 16), label, font=opt_label_font,
                  fill=ACCENT if not is_correct else CORRECT_TEXT)

        # Option text wrapped
        text = opts.get(key, "")
        text_lines = wrap_text(text, opt_font, col_w - 110)[:3]
        ty = oy + 16
        for line in text_lines:
            draw.text((x + 110, ty), line, font=opt_font, fill=TEXT if not is_correct else CORRECT_TEXT)
            ty += 44

        # Checkmark for correct (drawn with lines so we don't depend on Unicode glyph)
        if is_correct:
            cx0 = x + col_w - 80
            cy0 = oy + row_h // 2
            draw.line([(cx0, cy0), (cx0 + 18, cy0 + 18), (cx0 + 50, cy0 - 24)],
                      fill=CORRECT_TEXT, width=8)

    # Reason / Explanation box
    reason_y = options_top + 2 * row_h + 70
    reason_h = H - reason_y - 50
    draw.rounded_rectangle(
        [(60, reason_y), (W - 60, reason_y + reason_h)],
        radius=22, fill=REASON_BG,
    )
    why_font = font(34)
    why_label = f"Why  ({correct.upper()})"
    draw.text((90, reason_y + 18), why_label, font=why_font, fill=ACCENT)

    r_font = font(36)
    reason_lines = wrap_text(q["reason"], r_font, W - 200)
    ry = reason_y + 70
    for line in reason_lines[:4]:
        draw.text((90, ry), line, font=r_font, fill=TEXT)
        ry += 46

    img.save(path, quality=95)


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------
def build_narration_text(q: dict) -> str:
    """Build the spoken text for one question slide."""
    # Read the question, then options, then reveal answer + reason.
    opts = q["options"]
    correct = q["answer"].lower()
    answer_text = opts.get(correct, "")
    return (
        f"Question {q['q']}. {q['question']} "
        f"Option A, {opts.get('a','')}. "
        f"Option B, {opts.get('b','')}. "
        f"Option C, {opts.get('c','')}. "
        f"Option D, {opts.get('d','')}. "
        f"The correct answer is option {correct.upper()}, {answer_text}. "
        f"{q['reason']}"
    )


INTRO_NARRATION = (
    "Welcome aspirants. In this video we cover the complete answer key for UPSC "
    "Civil Services Preliminary Examination 2026, General Studies Paper 1, held on "
    "24th May 2026. We will go through all 100 questions with the correct answer "
    "and a quick explanation for each. Let's begin."
)

OUTRO_NARRATION = (
    "That brings us to the end of the GS Paper 1 answer key. "
    "Remember, the official UPSC answer key will be released soon, and some answers "
    "may change after objections. Do refer to the latest official key. "
    "If this video helped you, please like, share, and subscribe for more UPSC content. "
    "All the best for your results."
)


async def _tts_save(text: str, out_path: Path, voice: str = VOICE) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=VOICE_RATE)
    await communicate.save(str(out_path))


def generate_audio(items: list[tuple[str, str]]) -> None:
    """items = [(filename_stem, text), ...]. Saves <stem>.mp3 into AUDIO_DIR."""
    total = len(items)
    for i, (stem, text) in enumerate(items, 1):
        out = AUDIO_DIR / f"{stem}.mp3"
        if out.exists() and out.stat().st_size > 0:
            print(f"  [{i}/{total}] skip (cached) {stem}")
            continue
        print(f"  [{i}/{total}] tts -> {stem}")
        asyncio.run(_tts_save(text, out))


# ---------------------------------------------------------------------------
# ffmpeg helpers
# ---------------------------------------------------------------------------
def get_audio_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def make_slide_clip(slide_png: Path, audio_mp3: Path, out_mp4: Path,
                    extra_seconds: float = 0.6) -> None:
    """Render one MP4 from a still PNG + audio MP3, with a small trailing pause.

    Strategy: pad the AUDIO with silence first (via the [a]apad filtergraph on
    just the audio input), then -t to that total duration. Avoids the
    image-loop+apad memory bug we saw on Windows.
    """
    dur = get_audio_duration(audio_mp3) + extra_seconds
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "30", "-i", str(slide_png),
        "-i", str(audio_mp3),
        "-filter_complex", f"[1:a]apad=pad_dur={extra_seconds}[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-tune", "stillimage", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
        "-t", f"{dur:.3f}",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def concat_clips(clip_paths: list[Path], out_mp4: Path) -> None:
    list_file = OUT_DIR / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            # ffmpeg concat list: forward slashes and single-quoted paths
            f.write(f"file '{str(p).replace(chr(92), '/')}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def build_slides(data: dict) -> None:
    print("\n=== Rendering slides ===")
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    render_intro_slide(SLIDES_DIR / "00_intro.png")
    print("  intro slide ok")
    for q in data["questions"]:
        out = SLIDES_DIR / f"q{q['q']:03d}.png"
        render_question_slide(q, out)
    print(f"  rendered {len(data['questions'])} question slides")
    render_outro_slide(SLIDES_DIR / "99_outro.png")
    print("  outro slide ok")


def build_audio(data: dict) -> None:
    print("\n=== Generating TTS audio ===")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    items = [("00_intro", INTRO_NARRATION)]
    for q in data["questions"]:
        items.append((f"q{q['q']:03d}", build_narration_text(q)))
    items.append(("99_outro", OUTRO_NARRATION))
    generate_audio(items)


def assemble_video(data: dict) -> None:
    print("\n=== Assembling per-slide clips ===")
    clips_dir = OUT_DIR / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    order = ["00_intro"] + [f"q{q['q']:03d}" for q in data["questions"]] + ["99_outro"]
    clip_paths = []
    for i, stem in enumerate(order, 1):
        slide_png = SLIDES_DIR / (f"{stem}.png")
        audio_mp3 = AUDIO_DIR / f"{stem}.mp3"
        out_clip = clips_dir / f"{stem}.mp4"
        if not out_clip.exists() or out_clip.stat().st_size == 0:
            print(f"  [{i}/{len(order)}] encode {stem}")
            make_slide_clip(slide_png, audio_mp3, out_clip)
        else:
            print(f"  [{i}/{len(order)}] cached {stem}")
        clip_paths.append(out_clip)

    print("\n=== Concatenating final video ===")
    concat_clips(clip_paths, FINAL_VIDEO)
    print(f"\n[DONE] Final video: {FINAL_VIDEO}")
    print(f"       Total clips: {len(clip_paths)}")
    total = sum(get_audio_duration(AUDIO_DIR / f"{s}.mp3") for s in order)
    print(f"       Approx total duration: {total/60:.1f} min (audio sum)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slides", action="store_true")
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--assemble", action="store_true")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    do_all = not (args.slides or args.audio or args.assemble)
    if do_all or args.slides:
        build_slides(data)
    if do_all or args.audio:
        build_audio(data)
    if do_all or args.assemble:
        assemble_video(data)


if __name__ == "__main__":
    main()
