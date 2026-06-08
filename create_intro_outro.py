"""Create professional intro and subscribe outro videos.

Generates:
1. Intro (~6s): Logo zoom-in + channel name + voice narration
2. Outro (~8s): Subscribe animation + voice CTA + trough transition

Uses FFmpeg for video generation and edge-tts for voice.
"""

import asyncio
import math
import os
import subprocess
import sys

import edge_tts
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "assets/fonts/arial.ttf"
WATERMARK = "assets/watermark.png"
OUTPUT_DIR = "D:/temp"
TEMP_DIR = "D:/temp/intro_outro_temp"
WIDTH, HEIGHT = 1920, 1080
FPS = 30
CHANNEL_NAME = "Civil Services & Competitive Exam Prep"
VOICE = "en-IN-NeerjaNeural"


async def _generate_tts(text: str, output_path: str):
    """Generate TTS audio."""
    communicate = edge_tts.Communicate(text, VOICE, rate="-5%")
    await communicate.save(output_path)


def _run_ffmpeg(cmd, label="FFmpeg"):
    env = os.environ.copy()
    env["TEMP"] = "D:/temp"
    env["TMP"] = "D:/temp"
    result = subprocess.run(cmd, capture_output=True, text=True, env=env,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(f"  {label} ERROR: {result.stderr[-300:]}", file=sys.stderr)
        raise RuntimeError(f"{label} failed")


def create_intro(output_path: str):
    """Create a 5-second intro with logo animation and channel name."""
    print("  Creating intro frames...")
    frames_dir = os.path.join(TEMP_DIR, "intro_frames")
    os.makedirs(frames_dir, exist_ok=True)

    # Load assets
    logo = Image.open(WATERMARK).convert("RGBA")
    try:
        font_big = ImageFont.truetype(FONT_PATH, 48)
        font_small = ImageFont.truetype(FONT_PATH, 30)
    except (OSError, IOError):
        font_big = ImageFont.load_default()
        font_small = font_big

    total_frames = 6 * FPS  # 6 seconds

    for f in range(total_frames):
        t = f / FPS  # time in seconds
        progress = f / total_frames

        img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)

        # Phase 1 (0-1.5s): Dark background with particles/glow building up
        # Phase 2 (1.5-3.5s): Logo zooms in from large to normal with glow
        # Phase 3 (3.5-5s): Channel name fades in below logo

        # Gradient background: dark blue to black
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            r = int(5 + ratio * 10)
            g = int(10 + ratio * 20)
            b = int(30 + (1 - ratio) * 50)
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

        # Decorative accent lines (always visible, subtle)
        if t > 0.5:
            alpha = min(255, int((t - 0.5) * 200))
            line_y = HEIGHT // 2 - 120
            # Top accent line expanding from center
            line_width = int(min(1.0, (t - 0.5) / 1.5) * 400)
            center_x = WIDTH // 2
            draw.rectangle(
                [center_x - line_width, line_y, center_x + line_width, line_y + 2],
                fill=(255, 200, 0, alpha)
            )
            # Bottom accent line
            line_y2 = HEIGHT // 2 + 120
            draw.rectangle(
                [center_x - line_width, line_y2, center_x + line_width, line_y2 + 2],
                fill=(255, 200, 0, alpha)
            )

        # Logo animation
        if t > 0.8:
            logo_progress = min(1.0, (t - 0.8) / 1.5)
            # Ease out cubic
            ease = 1 - (1 - logo_progress) ** 3

            # Start large (3x), zoom to normal (1x)
            scale = 3.0 - ease * 2.0  # 3.0 -> 1.0
            logo_size = int(280 * scale)
            logo_resized = logo.resize((logo_size, logo_size), Image.LANCZOS)

            # Center position
            lx = (WIDTH - logo_size) // 2
            ly = (HEIGHT - logo_size) // 2 - 40

            # Glow effect behind logo
            if logo_progress < 0.7:
                glow_size = int(logo_size * 1.3)
                glow = Image.new("RGBA", (glow_size, glow_size), (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow)
                glow_alpha = int(80 * (1 - logo_progress))
                glow_draw.ellipse(
                    [0, 0, glow_size, glow_size],
                    fill=(255, 200, 50, glow_alpha)
                )
                gx = (WIDTH - glow_size) // 2
                gy = (HEIGHT - glow_size) // 2 - 40
                img.paste(glow, (gx, gy), glow)

            img.paste(logo_resized, (lx, ly), logo_resized)

        # Channel name fade in
        if t > 3.0:
            text_alpha = min(255, int((t - 3.0) * 180))
            text_y = HEIGHT // 2 + 130

            # Draw channel name centered
            bbox = draw.textbbox((0, 0), CHANNEL_NAME, font=font_big)
            tw = bbox[2] - bbox[0]
            tx = (WIDTH - tw) // 2

            # Shadow
            draw.text((tx + 2, text_y + 2), CHANNEL_NAME,
                      fill=(0, 0, 0, text_alpha), font=font_big)
            draw.text((tx, text_y), CHANNEL_NAME,
                      fill=(255, 255, 255, text_alpha), font=font_big)

            # Subtitle
            if t > 3.8:
                sub_alpha = min(255, int((t - 3.8) * 250))
                subtitle = "UPSC | IAS | Current Affairs"
                bbox2 = draw.textbbox((0, 0), subtitle, font=font_small)
                sw = bbox2[2] - bbox2[0]
                sx = (WIDTH - sw) // 2
                draw.text((sx, text_y + 60), subtitle,
                          fill=(255, 200, 100, sub_alpha), font=font_small)

        # Save frame
        img.convert("RGB").save(os.path.join(frames_dir, f"frame_{f:04d}.png"))

    print("  Generating intro voice...")
    voice_path = os.path.join(TEMP_DIR, "intro_voice.mp3")
    asyncio.run(_generate_tts(
        "Welcome to Civil Services and Competitive Exam Prep. "
        "Your one stop channel for UPSC and current affairs.",
        voice_path
    ))

    print("  Encoding intro video...")

    # Generate background tone
    whoosh_path = os.path.join(TEMP_DIR, "intro_sound.wav")
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        "sine=frequency=200:duration=6,volume=0.15,"
        "afade=t=in:st=0:d=1.5,afade=t=out:st=4:d=2",
        "-f", "lavfi", "-i",
        "sine=frequency=600:duration=6,volume=0.08,"
        "afade=t=in:st=0.5:d=2,afade=t=out:st=4:d=2",
        "-filter_complex", "[0][1]amix=inputs=2:duration=first",
        whoosh_path,
    ], "Intro sound")

    # Mix voice + background sound
    mixed_audio = os.path.join(TEMP_DIR, "intro_mixed.wav")
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-i", whoosh_path,
        "-i", voice_path,
        "-filter_complex",
        "[0]apad=whole_dur=6[bg];[1]adelay=1500|1500,apad=whole_dur=6[voice];"
        "[bg][voice]amix=inputs=2:duration=first:weights=0.4 1.0",
        "-t", "6",
        mixed_audio,
    ], "Audio mix")

    # Combine frames + mixed audio
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%04d.png"),
        "-i", mixed_audio,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path,
    ], "Intro encode")

    # Cleanup frames and temp audio
    for fname in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, fname))
    os.rmdir(frames_dir)
    for tmp in [whoosh_path, voice_path, mixed_audio]:
        if os.path.isfile(tmp):
            os.remove(tmp)

    size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Intro created: {output_path} ({size:.1f} MB)")


def create_outro(output_path: str):
    """Create an 8-second subscribe outro with trough/swoosh transition."""
    print("  Creating outro frames...")
    frames_dir = os.path.join(TEMP_DIR, "outro_frames")
    os.makedirs(frames_dir, exist_ok=True)

    logo = Image.open(WATERMARK).convert("RGBA")
    try:
        font_huge = ImageFont.truetype(FONT_PATH, 72)
        font_big = ImageFont.truetype(FONT_PATH, 48)
        font_med = ImageFont.truetype(FONT_PATH, 36)
        font_small = ImageFont.truetype(FONT_PATH, 28)
    except (OSError, IOError):
        font_huge = ImageFont.load_default()
        font_big = font_huge
        font_med = font_huge
        font_small = font_huge

    total_frames = 8 * FPS  # 8 seconds

    for f in range(total_frames):
        t = f / FPS
        img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)

        # Phase 1 (0-1.5s): Trough/swoosh transition - diagonal wipe from previous content
        # Phase 2 (1.5-4s): Subscribe button appears with bounce
        # Phase 3 (4-6s): Bell icon + "Like & Share" slides in
        # Phase 4 (6-8s): Logo + channel name + fade out

        # Background: dark red-black gradient
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            r = int(40 + (1 - ratio) * 30)
            g = int(5)
            b = int(10 + ratio * 20)
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

        # === TROUGH/SWOOSH TRANSITION (0-1.5s) ===
        if t < 1.5:
            # Diagonal wipe effect - white swoosh moving across screen
            swoosh_progress = t / 1.5
            ease = swoosh_progress ** 0.5  # ease out

            swoosh_x = int(ease * (WIDTH + 400)) - 400
            # Draw a bright diagonal swoosh band
            swoosh_width = 300
            for sx in range(swoosh_width):
                alpha = int(255 * math.sin(sx / swoosh_width * math.pi))
                x_pos = swoosh_x + sx
                if 0 <= x_pos < WIDTH:
                    # Diagonal: offset y based on x
                    for y in range(HEIGHT):
                        offset = int((y / HEIGHT) * 200)
                        actual_x = x_pos - offset
                        if 0 <= actual_x < WIDTH:
                            # Blend with existing
                            existing = img.getpixel((actual_x, y))
                            blend = min(255, existing[0] + alpha // 3)
                            blend_g = min(255, existing[1] + alpha // 4)
                            blend_b = min(255, existing[2] + alpha // 6)
                            img.putpixel((actual_x, y), (blend, blend_g, blend_b, 255))

            # Golden accent line following swoosh
            line_x = swoosh_x - 50
            if 0 < line_x < WIDTH:
                for y in range(HEIGHT):
                    offset = int((y / HEIGHT) * 200)
                    actual_x = line_x - offset
                    if 0 <= actual_x < WIDTH:
                        img.putpixel((actual_x, y), (255, 200, 0, 255))

        # === SUBSCRIBE BUTTON (1.5s+) ===
        if t > 1.2:
            btn_progress = min(1.0, (t - 1.2) / 0.8)
            # Bounce ease
            if btn_progress < 0.6:
                ease = (btn_progress / 0.6) ** 0.5
            elif btn_progress < 0.8:
                ease = 1.0 + 0.1 * math.sin((btn_progress - 0.6) / 0.2 * math.pi)
            else:
                ease = 1.0

            btn_w, btn_h = 500, 80
            btn_x = (WIDTH - btn_w) // 2  # perfectly centered horizontally
            btn_target_y = (HEIGHT - btn_h) // 2 - 40  # centered vertically, slightly above
            btn_y = int(btn_target_y + (1 - ease) * 200)

            # Red subscribe button
            draw.rounded_rectangle(
                [btn_x, btn_y, btn_x + btn_w, btn_y + btn_h],
                radius=12,
                fill=(204, 0, 0, 255)
            )
            # Button text
            sub_text = "SUBSCRIBE"
            bbox = draw.textbbox((0, 0), sub_text, font=font_huge)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((btn_x + (btn_w - tw) // 2, btn_y + (btn_h - th) // 2 - 5),
                      sub_text, fill=(255, 255, 255, 255), font=font_huge)

            # White border glow on button
            if t > 2.0 and t < 3.0:
                pulse = math.sin((t - 2.0) * math.pi * 3) * 0.5 + 0.5
                glow_alpha = int(100 * pulse)
                draw.rounded_rectangle(
                    [btn_x - 4, btn_y - 4, btn_x + btn_w + 4, btn_y + btn_h + 4],
                    radius=14,
                    outline=(255, 255, 255, glow_alpha),
                    width=3
                )

        # === BELL ICON + LIKE & SHARE (3.5s+) ===
        if t > 3.5:
            bell_progress = min(1.0, (t - 3.5) / 0.6)
            ease = 1 - (1 - bell_progress) ** 3

            # Bell text (using text as icon placeholder)
            bell_y = HEIGHT // 2 + 30
            bell_text = "Click the Bell Icon!"
            bbox = draw.textbbox((0, 0), bell_text, font=font_med)
            bw = bbox[2] - bbox[0]
            bell_x = (WIDTH - bw) // 2

            # Slide in from right
            offset_x = int((1 - ease) * 300)
            draw.text((bell_x + offset_x + 2, bell_y + 2), bell_text,
                      fill=(0, 0, 0, int(255 * ease)), font=font_med)
            draw.text((bell_x + offset_x, bell_y), bell_text,
                      fill=(255, 220, 100, int(255 * ease)), font=font_med)

            # Bell shake animation
            if t > 4.0 and t < 5.5:
                shake = math.sin((t - 4.0) * 15) * 5 * max(0, 1 - (t - 4.0) / 1.5)
                bell_icon_text = ">>  "
                draw.text((bell_x + offset_x - 60 + int(shake), bell_y), bell_icon_text,
                          fill=(255, 200, 0, 255), font=font_med)

        # === LIKE & SHARE (4.5s+) ===
        if t > 4.5:
            like_progress = min(1.0, (t - 4.5) / 0.6)
            ease = 1 - (1 - like_progress) ** 3

            like_y = HEIGHT // 2 + 90
            like_text = "Like  |  Share  |  Comment"
            bbox = draw.textbbox((0, 0), like_text, font=font_small)
            lw = bbox[2] - bbox[0]
            like_x = (WIDTH - lw) // 2

            draw.text((like_x, like_y), like_text,
                      fill=(200, 200, 200, int(255 * ease)), font=font_small)

        # === LOGO + CHANNEL NAME (5.5s+) ===
        if t > 5.5:
            logo_progress = min(1.0, (t - 5.5) / 1.0)
            ease = 1 - (1 - logo_progress) ** 2

            # Small logo at bottom
            logo_size = 100
            logo_small = logo.resize((logo_size, logo_size), Image.LANCZOS)
            logo_y = HEIGHT - 160
            logo_x = WIDTH // 2 - 250

            alpha_mask = logo_small.split()[3]
            alpha_mask = alpha_mask.point(lambda p: int(p * ease))
            logo_faded = logo_small.copy()
            logo_faded.putalpha(alpha_mask)
            img.paste(logo_faded, (logo_x, logo_y), logo_faded)

            # Channel name next to logo
            draw.text((logo_x + logo_size + 20, logo_y + 20),
                      CHANNEL_NAME,
                      fill=(255, 255, 255, int(255 * ease)), font=font_small)
            draw.text((logo_x + logo_size + 20, logo_y + 55),
                      "Subscribe for more!",
                      fill=(255, 200, 100, int(200 * ease)), font=font_small)

        # === FADE OUT (7s+) ===
        if t > 7.0:
            fade = (t - 7.0) / 1.0  # 0 to 1 over last second
            fade_overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, int(255 * fade)))
            img = Image.alpha_composite(img, fade_overlay)

        # Save frame
        img.convert("RGB").save(os.path.join(frames_dir, f"frame_{f:04d}.png"))

    print("  Generating outro voice...")
    voice_path = os.path.join(TEMP_DIR, "outro_voice.mp3")
    asyncio.run(_generate_tts(
        "If you found this video helpful, please subscribe to our channel "
        "and click the bell icon so you never miss an update. "
        "Like, share, and comment. Thank you for watching!",
        voice_path
    ))

    print("  Encoding outro video...")

    # Generate background chime
    sound_path = os.path.join(TEMP_DIR, "outro_sound.wav")
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        "sine=frequency=523:duration=8,volume=0.1,"
        "afade=t=in:st=0:d=0.5,afade=t=out:st=6:d=2",
        "-f", "lavfi", "-i",
        "sine=frequency=659:duration=8,volume=0.08,"
        "afade=t=in:st=1:d=0.5,afade=t=out:st=6:d=2",
        "-filter_complex", "[0][1]amix=inputs=2:duration=first",
        sound_path,
    ], "Outro sound")

    # Mix voice + background
    mixed_audio = os.path.join(TEMP_DIR, "outro_mixed.wav")
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-i", sound_path,
        "-i", voice_path,
        "-filter_complex",
        "[0]apad=whole_dur=8[bg];[1]adelay=1500|1500,apad=whole_dur=8[voice];"
        "[bg][voice]amix=inputs=2:duration=first:weights=0.3 1.0",
        "-t", "8",
        mixed_audio,
    ], "Outro audio mix")

    # Combine frames + mixed audio
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%04d.png"),
        "-i", mixed_audio,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path,
    ], "Outro encode")

    # Cleanup
    for fname in os.listdir(frames_dir):
        os.remove(os.path.join(frames_dir, fname))
    os.rmdir(frames_dir)
    for tmp in [sound_path, voice_path, mixed_audio]:
        if os.path.isfile(tmp):
            os.remove(tmp)

    size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Outro created: {output_path} ({size:.1f} MB)")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(TEMP_DIR, exist_ok=True)

    intro_path = os.path.join(OUTPUT_DIR, "channel_intro.mp4")
    outro_path = os.path.join(OUTPUT_DIR, "channel_subscribe_outro.mp4")

    print("=" * 60)
    print("  CREATING INTRO & OUTRO VIDEOS")
    print("=" * 60)

    print("\n[1/2] Creating Intro (5 seconds)...")
    create_intro(intro_path)

    print("\n[2/2] Creating Subscribe Outro (8 seconds)...")
    create_outro(outro_path)

    print(f"\n{'=' * 60}")
    print(f"  DONE!")
    print(f"  Intro:  {intro_path}")
    print(f"  Outro:  {outro_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
