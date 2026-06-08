"""Create a complete news-style video from a topic using AI.

Pipeline:
1. Generate script using GitHub Models (GPT-4o via OpenAI SDK)
2. Generate narration using edge-tts
3. Download relevant images from the web
4. Assemble slideshow video with text overlays, transitions, narration
5. Add watermark and branding

Usage:
    python create_news_video.py
    python create_news_video.py --topic "Your custom topic"
    python create_news_video.py --voice "hi-IN-SwaraNeural"  # Hindi voice
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import textwrap
import time
import re
from io import BytesIO

import edge_tts
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# Load .env file
load_dotenv()


# ============================================================
# CONFIG
# ============================================================
TOPIC = "India, South Korea plan $50 billion trade push with new deals"
TARGET_DURATION = 900  # 15 minutes in seconds
VOICE = "en-IN-NeerjaNeural"  # Indian English female voice
OUTPUT_DIR = "D:/temp"
ASSETS_DIR = "assets"
WATERMARK = "assets/watermark.png"
FONT_PATH = "assets/fonts/arial.ttf"
TEMP_DIR = "D:/temp/news_video_temp"

# Image settings
IMAGE_WIDTH = 1920
IMAGE_HEIGHT = 1080
SLIDE_DURATION = 25  # seconds per slide (will adjust based on narration)

# GitHub Models endpoint (uses OpenAI SDK)
GITHUB_MODELS_BASE = "https://models.inference.ai.azure.com"
GITHUB_MODEL = "gpt-4o"


# ============================================================
# STEP 1: Generate Script using AI
# ============================================================
def generate_script(topic: str, target_minutes: int = 15) -> dict:
    """Generate a detailed video script using GitHub Models API."""
    from openai import OpenAI

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not set in environment.")
        print("Set it with: export GITHUB_TOKEN=your_token")
        print("Get a token from: https://github.com/settings/tokens")
        sys.exit(1)

    client = OpenAI(base_url=GITHUB_MODELS_BASE, api_key=token)

    prompt = f"""You are an expert YouTube scriptwriter for a top current affairs educational channel focused on UPSC and competitive exams.

Create a VERY DETAILED {target_minutes}-minute video script about:
"{topic}"

Return a JSON object with this EXACT structure:
{{
    "title": "Catchy, SEO-friendly YouTube title (under 80 chars)",
    "description": "YouTube description (3 paragraphs with hashtags, exam relevance)",
    "tags": ["15+ relevant tags for YouTube SEO"],
    "thumbnail_text": "Short thumbnail text (max 6 words)",
    "sections": [
        {{
            "heading": "Section heading",
            "narration": "DETAILED narration text (250-350 words per section)",
            "image_search_query": "specific photo search query (e.g. 'India South Korea summit leaders handshake', 'semiconductor chip factory closeup', 'Seoul cityscape skyline night')",
            "key_points": ["key point 1", "key point 2", "key point 3", "key point 4"]
        }}
    ]
}}

CRITICAL REQUIREMENTS:
- You MUST create exactly 18-20 sections to fill {target_minutes} minutes
- Each section narration MUST be 250-350 words (at ~130 words/min narration speed, this gives ~2.5 min per section)
- The narration must be conversational, engaging, and educational
- Include specific numbers, statistics, dates, names of leaders, companies
- Cover ALL these topics: historical background, current trade volume, key sectors (semiconductors, defense, EV, steel, shipbuilding), CEPA agreement, strategic Indo-Pacific significance, economic impact on both countries, cultural ties, challenges, UPSC exam relevance, future outlook
- Image search queries must be SPECIFIC and likely to return real photos (use terms like 'photo', city names, company names, product photos)
- Each section should have 3-5 key points that will be shown as bullet points on screen
- End with a conclusion section asking viewers to subscribe

Return ONLY valid JSON, no markdown code fences."""

    print("Generating script with AI (this may take a minute)...")
    response = client.chat.completions.create(
        model=GITHUB_MODEL,
        messages=[
            {"role": "system", "content": "You are a scriptwriter. Return only valid JSON. No markdown. Create exactly 18-20 sections with 250-350 words of narration each."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=16000,
    )

    content = response.choices[0].message.content.strip()
    # Remove markdown code fences if present
    if content.startswith("```"):
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)

    script = json.loads(content)
    print(f"  Generated {len(script['sections'])} sections")
    print(f"  Title: {script['title']}")
    return script


# ============================================================
# STEP 2: Generate Narration Audio
# ============================================================
async def _generate_tts_async(text: str, output_path: str, voice: str):
    """Generate TTS audio for a single text segment."""
    communicate = edge_tts.Communicate(text, voice, rate="-10%")
    await communicate.save(output_path)


def generate_narration(sections: list[dict], voice: str, temp_dir: str) -> list[str]:
    """Generate narration audio for all sections."""
    audio_files = []
    total = len(sections)

    for i, section in enumerate(sections):
        audio_path = os.path.join(temp_dir, f"narration_{i:02d}.mp3")
        text = section["narration"]

        print(f"  [{i+1}/{total}] Generating audio: {section['heading'][:50]}...")
        asyncio.run(_generate_tts_async(text, audio_path, voice))

        if os.path.isfile(audio_path) and os.path.getsize(audio_path) > 0:
            audio_files.append(audio_path)
        else:
            print(f"    WARNING: Failed to generate audio for section {i+1}")

    return audio_files


# ============================================================
# STEP 3: Download Images
# ============================================================
def _search_wikimedia(query: str, limit: int = 5) -> list[str]:
    """Search Wikimedia Commons for images and return thumbnail URLs."""
    from urllib.parse import quote
    headers = {"User-Agent": "NewsVideoCreator/1.0 (educational project)"}
    encoded = quote(query)
    url = (
        f"https://commons.wikimedia.org/w/api.php?action=query"
        f"&generator=search&gsrsearch={encoded}&gsrlimit={limit}"
        f"&prop=imageinfo&iiprop=url|size&iiurlwidth=1920&format=json"
    )
    try:
        r = requests.get(url, timeout=10, headers=headers)
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        urls = []
        for page in pages.values():
            info = page.get("imageinfo", [{}])[0]
            thumb = info.get("thumburl", "")
            orig = info.get("url", "")
            # Prefer large thumbnails, skip SVG/PDF
            if thumb and not any(thumb.lower().endswith(ext) for ext in [".svg", ".pdf", ".ogg"]):
                urls.append(thumb)
            elif orig and not any(orig.lower().endswith(ext) for ext in [".svg", ".pdf", ".ogg"]):
                urls.append(orig)
        return urls
    except Exception:
        return []


def _search_bing_images(query: str, limit: int = 5) -> list[str]:
    """Scrape image URLs from Bing Image Search."""
    from urllib.parse import quote
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    encoded = quote(query)
    url = f"https://www.bing.com/images/search?q={encoded}&form=HDRSC2&first=1&tsc=ImageHoverTitle"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return []
        # Extract image URLs from murl parameter in the HTML
        pattern = r'murl&quot;:&quot;(https?://[^&]+?)&quot;'
        matches = re.findall(pattern, r.text)
        # Filter for common image formats
        image_urls = []
        for m in matches:
            if any(ext in m.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                image_urls.append(m)
            if len(image_urls) >= limit:
                break
        return image_urls
    except Exception:
        return []


def _download_image(url: str, output_path: str) -> bool:
    """Download an image and resize to slide dimensions."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, timeout=15, headers=headers, stream=True)
        if r.status_code != 200 or len(r.content) < 5000:
            return False
        img = Image.open(BytesIO(r.content)).convert("RGB")
        # Resize to cover 1920x1080 while maintaining aspect ratio
        img_ratio = img.width / img.height
        target_ratio = IMAGE_WIDTH / IMAGE_HEIGHT
        if img_ratio > target_ratio:
            new_h = IMAGE_HEIGHT
            new_w = int(new_h * img_ratio)
        else:
            new_w = IMAGE_WIDTH
            new_h = int(new_w / img_ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        # Center crop
        left = (new_w - IMAGE_WIDTH) // 2
        top = (new_h - IMAGE_HEIGHT) // 2
        img = img.crop((left, top, left + IMAGE_WIDTH, top + IMAGE_HEIGHT))
        img.save(output_path, quality=95)
        return True
    except Exception:
        return False


def download_images(sections: list[dict], temp_dir: str) -> list[str]:
    """Download real images for each section from Bing and Wikimedia."""
    image_files = []
    total = len(sections)
    used_urls = set()  # Avoid duplicates

    fallback_colors = [
        (0, 51, 102), (102, 0, 51), (0, 102, 51), (51, 51, 102),
        (102, 51, 0), (0, 76, 102), (76, 0, 102), (102, 76, 0),
        (0, 80, 80), (80, 40, 0), (60, 0, 90), (0, 60, 40),
        (90, 20, 20), (20, 60, 100), (70, 50, 0), (40, 0, 70),
        (0, 90, 60), (100, 40, 40), (30, 30, 80), (80, 60, 0),
    ]

    for i, section in enumerate(sections):
        img_path = os.path.join(temp_dir, f"slide_{i:02d}.png")
        query = section.get("image_search_query", section["heading"])

        print(f"  [{i+1}/{total}] Downloading image: {query[:50]}...")

        downloaded = False

        # Try Bing first (better quality images)
        if not downloaded:
            bing_urls = _search_bing_images(query)
            for url in bing_urls:
                if url in used_urls:
                    continue
                if _download_image(url, img_path):
                    used_urls.add(url)
                    downloaded = True
                    print(f"    [OK] Downloaded from Bing")
                    break

        # Try Wikimedia Commons
        if not downloaded:
            wiki_urls = _search_wikimedia(query)
            for url in wiki_urls:
                if url in used_urls:
                    continue
                if _download_image(url, img_path):
                    used_urls.add(url)
                    downloaded = True
                    print(f"    [OK] Downloaded from Wikimedia")
                    break

        # Try alternative queries if first attempt failed
        if not downloaded:
            alt_queries = [
                query.split(":")[0] if ":" in query else query.split(",")[0],
                " ".join(query.split()[:3]),
            ]
            for alt_q in alt_queries:
                if downloaded:
                    break
                for url in _search_bing_images(alt_q, limit=3):
                    if url in used_urls:
                        continue
                    if _download_image(url, img_path):
                        used_urls.add(url)
                        downloaded = True
                        print(f"    [OK] Downloaded (alt query: {alt_q[:30]})")
                        break

        if not downloaded:
            # Fallback: create styled slide with key points overlay
            img = _create_styled_slide(
                section["heading"],
                section.get("key_points", []),
                fallback_colors[i % len(fallback_colors)],
                i, total
            )
            img.save(img_path)
            print(f"    [FALLBACK] Created styled slide (no image found)")

        # Always overlay key points text on the downloaded image for readability
        if downloaded:
            _overlay_text_on_image(
                img_path, section["heading"],
                section.get("key_points", []),
                i, total
            )

        image_files.append(img_path)

    return image_files


def _overlay_text_on_image(img_path: str, heading: str, key_points: list,
                           index: int, total: int):
    """Add a slim bottom bar with heading only. Image stays 85%+ visible."""
    img = Image.open(img_path).convert("RGB")

    try:
        font_heading = ImageFont.truetype(FONT_PATH, 42)
        font_small = ImageFont.truetype(FONT_PATH, 20)
    except (OSError, IOError):
        font_heading = ImageFont.load_default()
        font_small = font_heading

    # Thin dark strip at very bottom only (15% of image height)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    bar_h = 120  # fixed pixel height for the bottom bar
    bar_y = IMAGE_HEIGHT - bar_h
    # Gradient-like bar: darker at bottom, transparent at top
    for y in range(bar_h):
        alpha = int(200 * (y / bar_h))  # 0 at top edge -> 200 at bottom
        overlay_draw.line([(0, bar_y + y), (IMAGE_WIDTH, bar_y + y)],
                          fill=(0, 0, 0, alpha))
    # Accent line
    overlay_draw.rectangle([0, bar_y, IMAGE_WIDTH, bar_y + 3], fill=(255, 200, 0, 200))

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Heading text - single line, truncated if needed
    heading_short = heading if len(heading) <= 55 else heading[:52] + "..."
    text_y = IMAGE_HEIGHT - 75
    # Shadow
    draw.text((42, text_y + 2), heading_short, fill=(0, 0, 0), font=font_heading)
    # Main text
    draw.text((40, text_y), heading_short, fill=(255, 255, 255), font=font_heading)

    # Section number - small, bottom-right
    draw.text((IMAGE_WIDTH - 140, IMAGE_HEIGHT - 35),
              f"{index + 1} / {total}",
              fill=(180, 180, 180), font=font_small)

    img.save(img_path, quality=95)


def _create_styled_slide(heading: str, key_points: list, base_color: tuple,
                         index: int, total: int) -> Image.Image:
    """Create a professional styled slide with gradient background."""
    img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT))
    draw = ImageDraw.Draw(img)

    # Create gradient background
    r, g, b = base_color
    for y in range(IMAGE_HEIGHT):
        ratio = y / IMAGE_HEIGHT
        cr = int(r * (1 - ratio * 0.5))
        cg = int(g * (1 - ratio * 0.5))
        cb = int(b * (1 - ratio * 0.5))
        draw.line([(0, y), (IMAGE_WIDTH, y)], fill=(cr, cg, cb))

    # Add decorative elements
    # Top bar
    draw.rectangle([0, 0, IMAGE_WIDTH, 8], fill=(255, 200, 0))
    # Bottom bar
    draw.rectangle([0, IMAGE_HEIGHT - 8, IMAGE_WIDTH, IMAGE_HEIGHT], fill=(255, 200, 0))

    # Side accent
    draw.rectangle([0, 100, 12, IMAGE_HEIGHT - 100], fill=(255, 200, 0, 180))

    # Load fonts
    try:
        font_heading = ImageFont.truetype(FONT_PATH, 58)
        font_points = ImageFont.truetype(FONT_PATH, 36)
        font_small = ImageFont.truetype(FONT_PATH, 24)
    except (OSError, IOError):
        font_heading = ImageFont.load_default()
        font_points = font_heading
        font_small = font_heading

    # Draw heading with text wrapping
    y_pos = 120
    wrapped = textwrap.wrap(heading, width=35)
    for line in wrapped[:3]:
        # Shadow
        draw.text((52, y_pos + 2), line, fill=(0, 0, 0, 128), font=font_heading)
        # Main text
        draw.text((50, y_pos), line, fill=(255, 255, 255), font=font_heading)
        y_pos += 70

    # Draw separator line
    y_pos += 20
    draw.line([(50, y_pos), (600, y_pos)], fill=(255, 200, 0), width=3)
    y_pos += 40

    # Draw key points with bullet markers
    for j, point in enumerate(key_points[:6]):
        if y_pos > IMAGE_HEIGHT - 150:
            break
        wrapped_point = textwrap.wrap(point, width=55)
        for k, line in enumerate(wrapped_point[:2]):
            prefix = "►  " if k == 0 else "    "
            color = (255, 220, 100) if k == 0 else (200, 200, 220)
            draw.text((70, y_pos), prefix + line, fill=color, font=font_points)
            y_pos += 48

        y_pos += 10

    # Section indicator
    draw.text((IMAGE_WIDTH - 200, IMAGE_HEIGHT - 60),
              f"Section {index + 1}/{total}",
              fill=(200, 200, 200, 180), font=font_small)

    return img


# ============================================================
# STEP 4: Assemble Video
# ============================================================
def get_audio_duration(path: str) -> float:
    """Get duration of an audio file using ffprobe."""
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ], capture_output=True, text=True)
    return float(result.stdout.strip()) if result.stdout.strip() else 30.0


def assemble_video(image_files: list[str], audio_files: list[str],
                   sections: list[dict], output_path: str,
                   watermark_path: str):
    """Assemble the final video using FFmpeg for reliability."""

    temp_dir = os.path.dirname(output_path) or "."
    num_sections = min(len(image_files), len(audio_files))

    if num_sections == 0:
        raise RuntimeError("No sections to assemble!")

    print(f"\n  Assembling {num_sections} sections...")

    # Step 1: Create individual section videos (image + audio)
    section_videos = []
    total_duration = 0

    for i in range(num_sections):
        section_video = os.path.join(temp_dir, f"_section_{i:02d}.mp4")
        duration = get_audio_duration(audio_files[i])
        total_duration += duration

        key_points = sections[i].get("key_points", [])[:4]

        # Build drawtext filters for key points that appear one by one
        font_file = FONT_PATH.replace("\\", "/")
        dt_filters = []

        num_pts = len(key_points)
        if num_pts > 0 and duration > 8:
            interval = (duration - 8) / num_pts
            for j, point in enumerate(key_points):
                appear_time = 3 + j * interval
                # Clean text for FFmpeg: remove problematic chars
                safe_text = (point
                    .replace("'", "\u2019")    # smart quote
                    .replace(":", " -")         # colon breaks ffmpeg
                    .replace("%", " percent")
                    .replace("\\", "")
                    .replace('"', ""))
                bullet = f">>  {safe_text}"
                y_pos = 60 + j * 55

                dt_filters.append(
                    f"drawtext=fontfile='{font_file}'"
                    f":text='{bullet}'"
                    f":fontcolor=white:fontsize=30"
                    f":x=40:y={y_pos}"
                    f":box=1:boxcolor=black@0.6:boxborderw=10"
                    f":enable='gte(t,{appear_time:.1f})'"
                )

        # Build full video filter
        vf_parts = ["format=yuv420p"]
        vf_parts.extend(dt_filters)
        vf_chain = ",".join(vf_parts)

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_files[i],
            "-i", audio_files[i],
            "-vf", vf_chain,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-t", str(duration),
            section_video,
        ]

        print(f"    Section {i+1}/{num_sections}: {duration:.1f}s - {sections[i]['heading'][:40]}...")

        env = os.environ.copy()
        env["TEMP"] = "D:/temp"
        env["TMP"] = "D:/temp"
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            # Fallback: simpler approach without drawtext (in case of escaping issues)
            print(f"    Retrying without text overlay...")
            cmd_simple = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", image_files[i],
                "-i", audio_files[i],
                "-vf", "format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                "-t", str(duration),
                section_video,
            ]
            result = subprocess.run(cmd_simple, capture_output=True, text=True, env=env)
            if result.returncode != 0:
                print(f"    ERROR: Section {i+1} failed: {result.stderr[-200:]}")
                continue

        section_videos.append(section_video)

    print(f"\n  Total duration: {total_duration:.0f}s ({total_duration/60:.1f} min)")

    # Step 2: Create concat file
    concat_file = os.path.join(temp_dir, "_concat_list.txt")
    with open(concat_file, "w") as f:
        for sv in section_videos:
            # Use forward slashes for ffmpeg on Windows
            sv_path = sv.replace("\\", "/")
            f.write(f"file '{sv_path}'\n")

    # Step 3: Concatenate all sections
    concat_output = os.path.join(temp_dir, "_concatenated.mp4")
    print("\n  Concatenating all sections...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        concat_output,
    ]
    env = os.environ.copy()
    env["TEMP"] = "D:/temp"
    env["TMP"] = "D:/temp"
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"  Concat error: {result.stderr[-300:]}")
        # Try re-encoding
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            concat_output,
        ]
        subprocess.run(cmd, capture_output=True, text=True, env=env)

    # Step 4: Add watermark overlay
    if os.path.isfile(watermark_path):
        print("  Adding watermark...")
        wm_width = int(IMAGE_WIDTH * 0.12)
        cmd = [
            "ffmpeg", "-y",
            "-i", concat_output,
            "-i", watermark_path,
            "-filter_complex",
            f"[1:v]scale={wm_width}:-1,format=rgba,colorchannelmixer=aa=0.7[wm];"
            f"[0:v][wm]overlay=W-w-20:H-h-20[out]",
            "-map", "[out]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "copy",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            print(f"  Watermark failed, using concatenated output directly")
            import shutil
            shutil.copy2(concat_output, output_path)
    else:
        import shutil
        shutil.copy2(concat_output, output_path)

    # Clean up temp files
    print("  Cleaning up temp files...")
    for sv in section_videos:
        try:
            os.remove(sv)
        except OSError:
            pass
    for f in [concat_file, concat_output]:
        try:
            os.remove(f)
        except OSError:
            pass

    return output_path


# ============================================================
# STEP 5: Create Thumbnail
# ============================================================
def create_thumbnail(title: str, thumbnail_text: str, output_path: str):
    """Create an eye-catching YouTube thumbnail."""
    img = Image.new("RGB", (1280, 720))
    draw = ImageDraw.Draw(img)

    # Gradient background (dark blue to red)
    for y in range(720):
        ratio = y / 720
        r = int(20 + ratio * 180)
        g = int(20 + (1 - ratio) * 30)
        b = int(100 + (1 - ratio) * 80)
        draw.line([(0, y), (1280, y)], fill=(r, g, b))

    # Add flag-colored accents
    # India tricolor stripe on left
    draw.rectangle([0, 0, 30, 240], fill=(255, 153, 51))   # Saffron
    draw.rectangle([0, 240, 30, 480], fill=(255, 255, 255)) # White
    draw.rectangle([0, 480, 30, 720], fill=(19, 136, 8))    # Green

    # South Korea colors on right
    draw.rectangle([1250, 0, 1280, 360], fill=(205, 46, 58))   # Red
    draw.rectangle([1250, 360, 1280, 720], fill=(0, 71, 160))  # Blue

    # Load fonts
    try:
        font_big = ImageFont.truetype(FONT_PATH, 72)
        font_med = ImageFont.truetype(FONT_PATH, 48)
        font_small = ImageFont.truetype(FONT_PATH, 36)
    except (OSError, IOError):
        font_big = ImageFont.load_default()
        font_med = font_big
        font_small = font_big

    # "$50 BILLION" big text
    y_pos = 80
    draw.text((82, y_pos + 3), "$50 BILLION", fill=(0, 0, 0), font=font_big)
    draw.text((80, y_pos), "$50 BILLION", fill=(255, 220, 0), font=font_big)
    y_pos += 100

    # "TRADE PUSH" text
    draw.text((82, y_pos + 3), "TRADE PUSH", fill=(0, 0, 0), font=font_big)
    draw.text((80, y_pos), "TRADE PUSH", fill=(255, 255, 255), font=font_big)
    y_pos += 120

    # Separator
    draw.rectangle([80, y_pos, 700, y_pos + 5], fill=(255, 220, 0))
    y_pos += 30

    # "INDIA × SOUTH KOREA"
    draw.text((82, y_pos + 2), "INDIA  ×  SOUTH KOREA", fill=(0, 0, 0), font=font_med)
    draw.text((80, y_pos), "INDIA  ×  SOUTH KOREA", fill=(255, 200, 100), font=font_med)
    y_pos += 80

    # "New Deals & Agreements"
    draw.text((82, y_pos + 2), "New Deals & Agreements", fill=(0, 0, 0), font=font_small)
    draw.text((80, y_pos), "New Deals & Agreements", fill=(200, 200, 220), font=font_small)

    # Bottom bar with channel branding
    draw.rectangle([0, 660, 1280, 720], fill=(0, 0, 0, 200))
    draw.text((50, 670), "Civil Services & Competitive Exam Prep",
              fill=(255, 220, 100), font=font_small)

    # Add watermark if available
    try:
        if os.path.isfile(WATERMARK):
            wm = Image.open(WATERMARK).convert("RGBA")
            wm_size = 150
            wm = wm.resize((wm_size, wm_size), Image.LANCZOS)
            img.paste(wm, (1280 - wm_size - 50, 50), wm)
    except Exception:
        pass

    img.save(output_path, quality=95)
    print(f"  Thumbnail saved: {output_path}")


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Create news video from topic using AI")
    parser.add_argument("--topic", default=TOPIC, help="Video topic")
    parser.add_argument("--duration", type=int, default=15, help="Target duration in minutes")
    parser.add_argument("--voice", default=VOICE, help="Edge TTS voice name")
    parser.add_argument("--output", default=None, help="Output video path")
    parser.add_argument("--skip-script", action="store_true", help="Skip script generation (use cached)")
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(TEMP_DIR, exist_ok=True)

    output_path = args.output or os.path.join(OUTPUT_DIR, "India_South_Korea_Trade_Deal.mp4")
    script_cache = os.path.join(TEMP_DIR, "script.json")
    thumbnail_path = output_path.replace(".mp4", "_thumbnail.jpg")

    print("=" * 60)
    print("  AI NEWS VIDEO CREATOR")
    print("=" * 60)
    print(f"  Topic: {args.topic}")
    print(f"  Duration: {args.duration} minutes")
    print(f"  Voice: {args.voice}")
    print(f"  Output: {output_path}")
    print("=" * 60)

    start_time = time.time()

    # STEP 1: Generate Script
    print("\n[STEP 1/5] Generating AI Script...")
    if args.skip_script and os.path.isfile(script_cache):
        with open(script_cache, "r", encoding="utf-8") as f:
            script = json.load(f)
        print(f"  Loaded cached script ({len(script['sections'])} sections)")
    else:
        script = generate_script(args.topic, args.duration)
        with open(script_cache, "w", encoding="utf-8") as f:
            json.dump(script, f, indent=2, ensure_ascii=False)
        print(f"  Script cached to {script_cache}")

    # STEP 2: Generate Narration
    print(f"\n[STEP 2/5] Generating Narration ({args.voice})...")
    audio_files = generate_narration(script["sections"], args.voice, TEMP_DIR)
    print(f"  Generated {len(audio_files)} audio segments")

    # STEP 3: Create/Download Images
    print(f"\n[STEP 3/5] Creating Slides & Downloading Images...")
    image_files = download_images(script["sections"], TEMP_DIR)
    print(f"  Created {len(image_files)} slides")

    # STEP 4: Assemble Video
    print(f"\n[STEP 4/5] Assembling Video...")
    assemble_video(image_files, audio_files, script["sections"],
                   output_path, WATERMARK)

    # STEP 5: Create Thumbnail
    print(f"\n[STEP 5/5] Creating Thumbnail...")
    create_thumbnail(
        script["title"],
        script.get("thumbnail_text", "India-South Korea Trade"),
        thumbnail_path,
    )

    # Summary
    elapsed = time.time() - start_time
    output_size = os.path.getsize(output_path) / (1024 * 1024) if os.path.isfile(output_path) else 0

    print(f"\n{'=' * 60}")
    print(f"  VIDEO CREATED SUCCESSFULLY!")
    print(f"{'=' * 60}")
    print(f"  Video:     {output_path} ({output_size:.1f} MB)")
    print(f"  Thumbnail: {thumbnail_path}")
    print(f"  Title:     {script['title']}")
    print(f"  Time:      {elapsed/60:.1f} minutes")
    print(f"{'=' * 60}")

    # Save upload metadata for later
    metadata = {
        "video_path": output_path,
        "thumbnail_path": thumbnail_path,
        "title": script["title"],
        "description": script.get("description", ""),
        "tags": script.get("tags", []),
        "category_id": "27",  # Education
        "privacy": "public",
    }
    meta_path = output_path.replace(".mp4", "_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Metadata:  {meta_path} (use for upload later)")


if __name__ == "__main__":
    main()
