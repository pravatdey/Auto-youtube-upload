"""Build UPSC Prelims 2026 GS Paper 1 explainer video — v2 (two-slide format).

Layout per question:
  slide A (question): stem + numbered statements + 4 options, no answer shown.
  slide B (answer):   same content + correct option highlighted + reason box.

Auto-fit logic: starts at a 'large' font size and shrinks down until everything
fits in the available vertical space.

Run:
    python build_video_v2.py                # full build (slides+audio+assemble)
    python build_video_v2.py --slides       # only re-render slides
    python build_video_v2.py --audio        # only re-generate audio
    python build_video_v2.py --assemble     # only re-assemble final MP4
    python build_video_v2.py --only 9 20 77 # render/audio/assemble only these question numbers (still includes intro/outro)
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parent
QUESTIONS_FILE = ROOT / "questions_v2.json"

OUT_DIR = Path("D:/temp/upsc_2026_video_v2")
SLIDES_DIR = OUT_DIR / "slides"
AUDIO_DIR = OUT_DIR / "audio"
CLIPS_DIR = OUT_DIR / "clips"
FINAL_VIDEO = OUT_DIR / "UPSC_Prelims_2026_GS1_AnswerKey_v2.mp4"

W, H = 1920, 1080
FONT_PATH = str(REPO_ROOT / "assets/fonts/arial.ttf")
FONT_PATH_BOLD = str(REPO_ROOT / "assets/fonts/arialbd.ttf")

VOICE = "en-IN-NeerjaNeural"
VOICE_RATE = "+0%"

# Colours
BG_TOP = (15, 23, 42)
BG_BOTTOM = (30, 41, 59)
ACCENT = (250, 204, 21)
TEXT = (248, 250, 252)
SUBTLE = (148, 163, 184)
OPTION_BG = (51, 65, 85)
CORRECT_BG = (16, 185, 129)
CORRECT_TEXT = (255, 255, 255)
STATEMENT_BG = (30, 41, 59)
STATEMENT_BORDER = (71, 85, 105)
REASON_BG = (30, 64, 175)


# ---------------------------------------------------------------------------
# Font + text helpers
# ---------------------------------------------------------------------------
_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_PATH_BOLD if (bold and Path(FONT_PATH_BOLD).exists()) else FONT_PATH
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def wrap_text(text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap text. Respects explicit \\n line breaks."""
    out = []
    for raw_line in text.split("\n"):
        if not raw_line.strip():
            out.append("")
            continue
        words = raw_line.split()
        cur = words[0]
        for w in words[1:]:
            trial = cur + " " + w
            if fnt.getbbox(trial)[2] <= max_width:
                cur = trial
            else:
                out.append(cur)
                cur = w
        out.append(cur)
    return out


def draw_gradient_bg(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


# ---------------------------------------------------------------------------
# Intro / outro slides
# ---------------------------------------------------------------------------
def render_intro_slide(path: Path) -> None:
    img = Image.new("RGB", (W, H))
    draw_gradient_bg(img)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (W, 12)], fill=ACCENT)
    draw.rectangle([(0, H - 12), (W, H)], fill=ACCENT)

    title = "UPSC Prelims 2026"
    paper = "GS Paper 1 — Complete Answer Key"
    cta = "Verbatim Questions + Explanations"
    date = "Exam: 24 May 2026  |  Set D  |  100 Questions"

    def cx(text, fnt):
        bbox = fnt.getbbox(text)
        return (W - (bbox[2] - bbox[0])) // 2

    f_title = font(110, bold=True)
    f_sub = font(56)
    f_small = font(40)
    draw.text((cx(title, f_title), 280), title, font=f_title, fill=TEXT)
    draw.text((cx(paper, f_sub), 430), paper, font=f_sub, fill=ACCENT)
    draw.text((cx(cta, f_sub), 530), cta, font=f_sub, fill=TEXT)
    draw.text((cx(date, f_small), 700), date, font=f_small, fill=SUBTLE)
    img.save(path, quality=95)


def render_outro_slide(path: Path) -> None:
    img = Image.new("RGB", (W, H))
    draw_gradient_bg(img)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (W, 12)], fill=ACCENT)
    draw.rectangle([(0, H - 12), (W, H)], fill=ACCENT)

    def cx(text, fnt):
        bbox = fnt.getbbox(text)
        return (W - (bbox[2] - bbox[0])) // 2

    f_title = font(110, bold=True)
    f_sub = font(60)
    f_small = font(44)
    draw.text((cx("All the Best!", f_title), 300), "All the Best!", font=f_title, fill=ACCENT)
    draw.text((cx("Like, Share & Subscribe", f_sub), 470), "Like, Share & Subscribe",
              font=f_sub, fill=TEXT)
    note = "Official UPSC answer key will be released soon"
    note2 = "Some answers may change — refer to the latest official key"
    draw.text((cx(note, f_small), 650), note, font=f_small, fill=SUBTLE)
    draw.text((cx(note2, f_small), 720), note2, font=f_small, fill=SUBTLE)
    img.save(path, quality=95)


# ---------------------------------------------------------------------------
# Question slide rendering (the heart of v2)
# ---------------------------------------------------------------------------
def layout_question(q: dict, with_answer: bool):
    """Compute total height of all content for a given font size config.

    Returns the list of draw instructions for the renderer."""
    pass  # logic is inlined in render_question_slide below


def parse_match_table(stem: str):
    """If stem contains a Match List I/II table, return (intro_line, headers, rows).
    Otherwise return None.

    Handles two real-world patterns:
      Pattern A — intro with parens carrying labels, then A./B./C./D. rows:
        Match List I (Project ...) with List II (Country):
        A. Foo    1. Bar
        B. ...
      Pattern B — separate header line:
        Match List I with List II ...:
        List I (Header1)    List II (Header2)
        A. Foo    1. Bar
        ...
    """
    import re as _re
    if "List I" not in stem:
        return None
    lines = [ln.rstrip() for ln in stem.split("\n") if ln.strip()]
    if len(lines) < 2:
        return None

    intro_line = lines[0]
    rest = lines[1:]

    # Try to find an explicit header line "List I ... List II ..."
    headers = None
    header_idx = None
    for i, ln in enumerate(rest):
        if "List I" in ln and "List II" in ln:
            idx = ln.find("List II")
            headers = (ln[:idx].strip(), ln[idx:].strip())
            header_idx = i
            break

    # If no explicit header line, derive headers from the parens in the intro
    if headers is None:
        m_left = _re.search(r"List I\s*\(([^)]+)\)", intro_line)
        m_right = _re.search(r"List II\s*\(([^)]+)\)", intro_line)
        if m_left and m_right:
            headers = (f"List I — {m_left.group(1).strip()}",
                       f"List II — {m_right.group(1).strip()}")
            intro_line = "Match the following:"

    # Extract A./B./C./D. rows
    rows = []
    row_lines = rest if header_idx is None else rest[header_idx + 1:]
    for ln in row_lines:
        stripped = ln.strip()
        if len(stripped) >= 2 and stripped[0] in "ABCD" and stripped[1] == ".":
            m = list(_re.finditer(r"\s+(\d\.\s*)", stripped))
            if m:
                last = m[-1]
                left = stripped[:last.start()].strip()
                right = stripped[last.start():].strip()
                rows.append((left, right))
            else:
                rows.append((stripped, ""))

    if rows and headers is not None:
        return (intro_line, headers, rows)
    return None


def render_question_slide(q: dict, path: Path, reveal: bool) -> None:
    """Render one slide.

    reveal=False -> question slide (no answer highlight, no reason box)
    reveal=True  -> answer slide  (correct option highlighted + reason box visible)
    """
    img = Image.new("RGB", (W, H))
    draw_gradient_bg(img)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (W, 8)], fill=ACCENT)
    draw.rectangle([(0, H - 8), (W, H)], fill=ACCENT)

    # Header
    h_font = font(40, bold=True)
    draw.text((60, 30), f"Q{q['q']} / 100", font=h_font, fill=ACCENT)
    topic = q.get("topic", "")
    if topic:
        topic_font = font(30)
        tw = topic_font.getbbox(topic)[2]
        draw.rounded_rectangle(
            [(W - 60 - tw - 40, 30), (W - 60, 84)],
            radius=14, fill=OPTION_BG,
        )
        draw.text((W - 60 - tw - 20, 42), topic, font=topic_font, fill=TEXT)

    content_top = 110
    reason_h = 220 if reveal else 0
    content_bottom = H - 30 - (reason_h + 20 if reveal else 0)
    available_h = content_bottom - content_top
    content_left = 60
    content_right = W - 60
    content_w = content_right - content_left

    stem = q["stem"]
    statements = q.get("statements") or []
    select_prompt = q.get("select_prompt") or ""
    options = q["options"]
    correct = q["answer"].lower()

    # Detect match-table questions — render specially as a real table
    match_table = parse_match_table(stem)

    # Auto-fit: try font sizes from large to small until everything fits.
    candidate_configs = [
        # (stem_sz, stmt_sz, prompt_sz, opt_sz, stmt_pad, opt_pad_y, gap)
        (42, 38, 36, 36, 14, 14, 18),
        (38, 34, 32, 32, 12, 12, 16),
        (34, 30, 28, 28, 10, 10, 14),
        (30, 26, 24, 26, 9, 9, 12),
        (26, 22, 22, 22, 8, 8, 10),
        (22, 20, 20, 20, 6, 6, 8),
    ]

    table = parse_match_table(stem)

    chosen = None
    chosen_layout = None
    for stem_sz, stmt_sz, prompt_sz, opt_sz, stmt_pad, opt_pad_y, gap in candidate_configs:
        f_stem = font(stem_sz)
        f_stmt = font(stmt_sz)
        f_prompt = font(prompt_sz)
        f_opt = font(opt_sz)
        f_opt_lbl = font(opt_sz, bold=True)

        line_h = lambda f: f.getbbox("Ag")[3] - f.getbbox("Ag")[1] + 8

        layout = []  # list of ('section', payload, height) entries

        if table is not None:
            intro, headers, rows = table
            intro_lines = wrap_text(intro, f_stem, content_w)
            h_intro = len(intro_lines) * line_h(f_stem)
            layout.append(("stem", (intro_lines, f_stem, line_h(f_stem)), h_intro))

            # Table: two columns
            tbl_col_w = (content_w - 32) // 2
            f_th = font(stmt_sz, bold=True)
            # Pre-wrap each row's left/right
            wrapped_rows = []
            for left, right in rows:
                l_lines = wrap_text(left, f_stmt, tbl_col_w - 20)
                r_lines = wrap_text(right, f_stmt, tbl_col_w - 20)
                max_lines = max(len(l_lines), len(r_lines))
                wrapped_rows.append((l_lines, r_lines, max_lines))
            header_h = line_h(f_th) + 16
            row_pad = 8
            row_heights = [mx * line_h(f_stmt) + 2 * row_pad for _, _, mx in wrapped_rows]
            table_h = header_h + sum(row_heights) + 6
            layout.append(("gap", None, gap))
            layout.append(("table", (headers, wrapped_rows, f_th, f_stmt,
                                     tbl_col_w, header_h, row_pad, line_h(f_stmt),
                                     row_heights), table_h))
        else:
            # Stem
            stem_lines = wrap_text(stem, f_stem, content_w)
            h_stem = len(stem_lines) * line_h(f_stem)
            layout.append(("stem", (stem_lines, f_stem, line_h(f_stem)), h_stem))

        # Statements (each in its own box)
        if statements:
            layout.append(("gap", None, gap))
            for idx, st in enumerate(statements, 1):
                # We'll put the number left-padded
                text = f"{idx}. {st}"
                lines = wrap_text(text, f_stmt, content_w - 24)
                box_h = len(lines) * line_h(f_stmt) + 2 * stmt_pad
                layout.append(("stmt_box", (lines, f_stmt, line_h(f_stmt), stmt_pad), box_h + 6))

        # Select prompt
        if select_prompt:
            layout.append(("gap", None, gap))
            prompt_lines = wrap_text(select_prompt, f_prompt, content_w)
            h_prompt = len(prompt_lines) * line_h(f_prompt)
            layout.append(("prompt", (prompt_lines, f_prompt, line_h(f_prompt)), h_prompt))

        # Options grid (2x2)
        layout.append(("gap", None, gap))
        col_w = (content_w - 32) // 2  # 32 px gutter between cols
        opt_max_lines = 0
        opt_line_h = line_h(f_opt)
        opt_lines_each = []
        for k in ["a", "b", "c", "d"]:
            text = options.get(k, "")
            lines = wrap_text(text, f_opt, col_w - 100)
            opt_lines_each.append(lines)
            opt_max_lines = max(opt_max_lines, len(lines))
        row_h = opt_max_lines * opt_line_h + 2 * opt_pad_y
        opt_grid_h = 2 * row_h + 24  # two rows + inner gutter
        layout.append(("opts", (opt_lines_each, f_opt, f_opt_lbl, col_w, row_h, opt_pad_y, opt_line_h), opt_grid_h))

        total_h = sum(item[2] for item in layout)
        if total_h <= available_h:
            chosen = (stem_sz, stmt_sz, prompt_sz, opt_sz, stmt_pad, opt_pad_y, gap)
            chosen_layout = layout
            break

    if chosen_layout is None:
        # Use smallest config anyway (will overflow slightly)
        chosen_layout = layout
        chosen = candidate_configs[-1]

    # Render
    y = content_top
    for kind, payload, h in chosen_layout:
        if kind == "gap":
            y += h
            continue
        if kind == "stem":
            lines, f_stem, lh = payload
            for ln in lines:
                draw.text((content_left, y), ln, font=f_stem, fill=TEXT)
                y += lh
        elif kind == "stmt_box":
            lines, f_stmt, lh, pad = payload
            box_h = len(lines) * lh + 2 * pad
            draw.rounded_rectangle(
                [(content_left, y), (content_right, y + box_h)],
                radius=10, fill=STATEMENT_BG, outline=STATEMENT_BORDER, width=1,
            )
            ty = y + pad
            for ln in lines:
                draw.text((content_left + 16, ty), ln, font=f_stmt, fill=TEXT)
                ty += lh
            y += box_h + 6
        elif kind == "table":
            (headers, wrapped_rows, f_th, f_stmt_local, tbl_col_w,
             header_h, row_pad, stmt_lh, row_heights) = payload
            left_col_x = content_left
            right_col_x = content_left + tbl_col_w + 32

            # Header row
            draw.rounded_rectangle(
                [(left_col_x, y), (left_col_x + tbl_col_w, y + header_h - 6)],
                radius=8, fill=OPTION_BG,
            )
            draw.rounded_rectangle(
                [(right_col_x, y), (right_col_x + tbl_col_w, y + header_h - 6)],
                radius=8, fill=OPTION_BG,
            )
            draw.text((left_col_x + 14, y + 6), headers[0], font=f_th, fill=ACCENT)
            draw.text((right_col_x + 14, y + 6), headers[1], font=f_th, fill=ACCENT)
            y += header_h

            # Rows
            for (l_lines, r_lines, _), rh in zip(wrapped_rows, row_heights):
                draw.rounded_rectangle(
                    [(left_col_x, y), (left_col_x + tbl_col_w, y + rh)],
                    radius=8, fill=STATEMENT_BG, outline=STATEMENT_BORDER, width=1,
                )
                draw.rounded_rectangle(
                    [(right_col_x, y), (right_col_x + tbl_col_w, y + rh)],
                    radius=8, fill=STATEMENT_BG, outline=STATEMENT_BORDER, width=1,
                )
                lty = y + row_pad
                for ln in l_lines:
                    draw.text((left_col_x + 14, lty), ln, font=f_stmt_local, fill=TEXT)
                    lty += stmt_lh
                rty = y + row_pad
                for ln in r_lines:
                    draw.text((right_col_x + 14, rty), ln, font=f_stmt_local, fill=TEXT)
                    rty += stmt_lh
                y += rh + 4
        elif kind == "prompt":
            lines, f_prompt, lh = payload
            for ln in lines:
                draw.text((content_left, y), ln, font=f_prompt, fill=ACCENT)
                y += lh
        elif kind == "opts":
            opt_lines_each, f_opt, f_opt_lbl, col_w, row_h, opt_pad_y, opt_line_h = payload
            positions = [
                ("a", content_left, y),
                ("b", content_left + col_w + 32, y),
                ("c", content_left, y + row_h + 24),
                ("d", content_left + col_w + 32, y + row_h + 24),
            ]
            for i, (key, x, oy) in enumerate(positions):
                is_correct = reveal and (key == correct)
                bg = CORRECT_BG if is_correct else OPTION_BG
                draw.rounded_rectangle([(x, oy), (x + col_w, oy + row_h)],
                                       radius=14, fill=bg)
                label = f"({key.upper()})"
                draw.text((x + 18, oy + opt_pad_y), label, font=f_opt_lbl,
                          fill=ACCENT if not is_correct else CORRECT_TEXT)
                # text indent
                ty = oy + opt_pad_y
                for ln in opt_lines_each[i]:
                    draw.text((x + 100, ty), ln, font=f_opt,
                              fill=TEXT if not is_correct else CORRECT_TEXT)
                    ty += opt_line_h
                if is_correct:
                    # checkmark drawn via lines
                    cx0 = x + col_w - 70
                    cy0 = oy + row_h // 2
                    draw.line([(cx0, cy0), (cx0 + 18, cy0 + 18),
                               (cx0 + 48, cy0 - 22)],
                              fill=CORRECT_TEXT, width=7)
            y += 2 * row_h + 24

    # Reason box (only on reveal slide)
    if reveal:
        ry = H - 30 - reason_h
        draw.rounded_rectangle(
            [(60, ry), (W - 60, ry + reason_h)],
            radius=16, fill=REASON_BG,
        )
        f_why_lbl = font(32, bold=True)
        draw.text((90, ry + 16), f"Why  ({correct.upper()})",
                  font=f_why_lbl, fill=ACCENT)
        f_reason = font(32)
        reason_lines = wrap_text(q["reason"], f_reason, W - 200)
        # auto-shrink if too many lines
        if len(reason_lines) > 4:
            f_reason = font(28)
            reason_lines = wrap_text(q["reason"], f_reason, W - 200)
        line_h_r = f_reason.getbbox("Ag")[3] - f_reason.getbbox("Ag")[1] + 6
        ty = ry + 64
        for ln in reason_lines[:5]:
            draw.text((90, ty), ln, font=f_reason, fill=TEXT)
            ty += line_h_r
    else:
        # Subtle "Think it through..." hint at bottom of question slide
        hint_font = font(28)
        hint = "Take a moment to think..."
        bbox = hint_font.getbbox(hint)
        draw.text(((W - (bbox[2] - bbox[0])) // 2, H - 60),
                  hint, font=hint_font, fill=SUBTLE)

    img.save(path, quality=92)


# ---------------------------------------------------------------------------
# TTS narration
# ---------------------------------------------------------------------------
INTRO_NARRATION = (
    "Welcome aspirants. In this video we cover the complete answer key for UPSC "
    "Civil Services Preliminary Examination 2026, General Studies Paper 1, held on "
    "24th May 2026. For every one of the 100 questions, we'll read the question in full, "
    "give you a moment to think, then reveal the correct answer with a quick explanation. "
    "Let's begin."
)

OUTRO_NARRATION = (
    "That brings us to the end of the GS Paper 1 answer key. "
    "The official UPSC answer key will be released soon, and some answers "
    "may change after the objection process. Please refer to the latest official key. "
    "If this video helped you, please like, share, and subscribe for more UPSC content. "
    "All the best for your results."
)


def narration_for_question(q: dict) -> str:
    """Reading of the question (slide A)."""
    parts = [f"Question {q['q']}."]
    parts.append(q["stem"])
    statements = q.get("statements") or []
    for i, st in enumerate(statements, 1):
        parts.append(f"Statement {i}. {st}")
    select_prompt = q.get("select_prompt") or ""
    if select_prompt:
        parts.append(select_prompt)
    opts = q["options"]
    parts.append(f"Option A. {opts.get('a','')}")
    parts.append(f"Option B. {opts.get('b','')}")
    parts.append(f"Option C. {opts.get('c','')}")
    parts.append(f"Option D. {opts.get('d','')}")
    return " ".join(parts)


def narration_for_answer(q: dict) -> str:
    """Reveal of correct answer + reason (slide B)."""
    correct = q["answer"].lower()
    opt_text = q["options"].get(correct, "")
    return (
        f"The correct answer is option {correct.upper()}. {opt_text}. "
        f"{q['reason']}"
    )


async def _tts_save(text: str, out_path: Path, voice: str = VOICE) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=VOICE_RATE)
    await communicate.save(str(out_path))


def generate_audio(items: list[tuple[str, str]]) -> None:
    total = len(items)
    for i, (stem, text) in enumerate(items, 1):
        out = AUDIO_DIR / f"{stem}.mp3"
        if out.exists() and out.stat().st_size > 0:
            print(f"  [{i}/{total}] skip (cached) {stem}")
            continue
        print(f"  [{i}/{total}] tts -> {stem}")
        asyncio.run(_tts_save(text, out))


# ---------------------------------------------------------------------------
# ffmpeg
# ---------------------------------------------------------------------------
def get_audio_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def make_slide_clip(slide_png: Path, audio_mp3: Path, out_mp4: Path,
                    extra_seconds: float = 0.5, retries: int = 2) -> None:
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
    last_err = None
    for _ in range(retries + 1):
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return
        except subprocess.CalledProcessError as e:
            last_err = e
            # Retry on transient memory errors
    raise last_err


def concat_clips(clip_paths: list[Path], out_mp4: Path) -> None:
    list_file = OUT_DIR / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
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
def build_slides(data: dict, only: set[int] | None = None) -> None:
    print("\n=== Rendering slides ===")
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    if only is None:
        render_intro_slide(SLIDES_DIR / "00_intro.png")
        render_outro_slide(SLIDES_DIR / "99_outro.png")
        print("  intro + outro ok")
    for q in data["questions"]:
        if only is not None and q["q"] not in only:
            continue
        render_question_slide(q, SLIDES_DIR / f"q{q['q']:03d}_q.png", reveal=False)
        render_question_slide(q, SLIDES_DIR / f"q{q['q']:03d}_a.png", reveal=True)
    print(f"  rendered question/answer slides ({len(data['questions']) if only is None else len(only)} questions x 2)")


def build_audio(data: dict, only: set[int] | None = None) -> None:
    print("\n=== Generating TTS audio ===")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    if only is None:
        items.append(("00_intro", INTRO_NARRATION))
    for q in data["questions"]:
        if only is not None and q["q"] not in only:
            continue
        items.append((f"q{q['q']:03d}_q", narration_for_question(q)))
        items.append((f"q{q['q']:03d}_a", narration_for_answer(q)))
    if only is None:
        items.append(("99_outro", OUTRO_NARRATION))
    generate_audio(items)


def assemble_video(data: dict) -> None:
    print("\n=== Encoding per-slide clips ===")
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    order = ["00_intro"]
    for q in data["questions"]:
        order.append(f"q{q['q']:03d}_q")
        order.append(f"q{q['q']:03d}_a")
    order.append("99_outro")

    clip_paths = []
    for i, stem in enumerate(order, 1):
        slide_png = SLIDES_DIR / f"{stem}.png"
        audio_mp3 = AUDIO_DIR / f"{stem}.mp3"
        out_clip = CLIPS_DIR / f"{stem}.mp4"
        if not out_clip.exists() or out_clip.stat().st_size == 0:
            print(f"  [{i}/{len(order)}] encode {stem}")
            make_slide_clip(slide_png, audio_mp3, out_clip)
        else:
            print(f"  [{i}/{len(order)}] cached {stem}")
        clip_paths.append(out_clip)

    print("\n=== Concatenating final video ===")
    concat_clips(clip_paths, FINAL_VIDEO)
    total = sum(get_audio_duration(AUDIO_DIR / f"{s}.mp3") for s in order)
    print(f"\n[DONE] Final video: {FINAL_VIDEO}")
    print(f"       Total clips: {len(clip_paths)}")
    print(f"       Approx duration: {total/60:.1f} min")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slides", action="store_true")
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--only", nargs="*", type=int, default=None,
                    help="Limit slides/audio steps to specific question numbers")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    only = set(args.only) if args.only else None
    do_all = not (args.slides or args.audio or args.assemble)
    if do_all or args.slides:
        build_slides(data, only=only)
    if do_all or args.audio:
        build_audio(data, only=only)
    if do_all or args.assemble:
        assemble_video(data)


if __name__ == "__main__":
    main()
