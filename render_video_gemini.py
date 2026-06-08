"""
Render final video using Gemini-generated audio clips.
Reuses visual frame functions from create_opsc_video_with_audio.py.
"""
import os
import subprocess
import json
import shutil
import sys

# Reuse visual frame creation from existing script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from create_opsc_video_with_audio import (
    QUESTIONS, WIDTH, HEIGHT, OUTPUT_DIR,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, PURPLE,
    create_intro_frame, create_section_divider, create_question_frame,
    create_answer_frame, create_outro_frame
)

AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio_gemini")
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames_gemini")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "opsc_ocs_prelims_2024_GEMINI.mp4")

os.makedirs(FRAMES_DIR, exist_ok=True)


def get_audio_duration(filepath):
    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filepath]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(json.loads(result.stdout)['format']['duration'])


def main():
    print("=" * 60)
    print("RENDER VIDEO with Gemini Audio")
    print("=" * 60)

    # Check audio is generated
    expected_clips = ["intro.mp3", "outro.mp3"] + \
                     [f"section_{i}.mp3" for i in range(4)] + \
                     [f"q_{i:03d}.mp3" for i in range(1, 101)] + \
                     [f"a_{i:03d}.mp3" for i in range(1, 101)]
    missing = [c for c in expected_clips if not os.path.exists(os.path.join(AUDIO_DIR, c))]
    if missing:
        print(f"ERROR: {len(missing)} audio clips missing. Run generate_gemini_audio.py first.")
        print(f"   First few missing: {missing[:5]}")
        sys.exit(1)
    print(f"All {len(expected_clips)} audio clips found.")

    # Build segments list
    PADDING = 1.0  # extra seconds after audio
    MIN_Q_DUR = 5
    MIN_A_DUR = 6

    print("\n[1/3] Creating visual frames...")
    segments = []  # (img_path, audio_path, duration)

    # Intro
    intro_img = os.path.join(FRAMES_DIR, "intro.png")
    create_intro_frame().save(intro_img)
    intro_aud = os.path.join(AUDIO_DIR, "intro.mp3")
    segments.append((intro_img, intro_aud, max(6, get_audio_duration(intro_aud) + PADDING)))

    sections = [
        ("Section 1: Polity & History", "Questions 1-25"),
        ("Section 2: Geography & Economy", "Questions 26-50"),
        ("Section 3: Science & Current Affairs", "Questions 51-75"),
        ("Section 4: Odisha & Miscellaneous", "Questions 76-100"),
    ]
    sec_colors = [ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, PURPLE]

    for idx, q in enumerate(QUESTIONS):
        if idx % 25 == 0:
            sec_idx = idx // 25
            sec_img = os.path.join(FRAMES_DIR, f"sec_{sec_idx}.png")
            create_section_divider(sections[sec_idx][0], sections[sec_idx][1], sec_colors[sec_idx]).save(sec_img)
            sec_aud = os.path.join(AUDIO_DIR, f"section_{sec_idx}.mp3")
            segments.append((sec_img, sec_aud, max(4, get_audio_duration(sec_aud) + PADDING)))

        q_img = os.path.join(FRAMES_DIR, f"q_{q['q_no']:03d}.png")
        create_question_frame(q).save(q_img)
        q_aud = os.path.join(AUDIO_DIR, f"q_{q['q_no']:03d}.mp3")
        segments.append((q_img, q_aud, max(MIN_Q_DUR, get_audio_duration(q_aud) + PADDING)))

        a_img = os.path.join(FRAMES_DIR, f"a_{q['q_no']:03d}.png")
        create_answer_frame(q).save(a_img)
        a_aud = os.path.join(AUDIO_DIR, f"a_{q['q_no']:03d}.mp3")
        segments.append((a_img, a_aud, max(MIN_A_DUR, get_audio_duration(a_aud) + PADDING)))

        if (idx + 1) % 20 == 0:
            print(f"   ... processed {idx + 1}/100 questions")

    outro_img = os.path.join(FRAMES_DIR, "outro.png")
    create_outro_frame().save(outro_img)
    outro_aud = os.path.join(AUDIO_DIR, "outro.mp3")
    segments.append((outro_img, outro_aud, max(8, get_audio_duration(outro_aud) + PADDING)))

    total_dur = sum(d for _, _, d in segments)
    print(f"\n   Total segments: {len(segments)}, Duration: {int(total_dur)//60}m {int(total_dur)%60}s")

    # Render each segment
    print("\n[2/3] Rendering segments with ffmpeg...")
    seg_files = []
    for i, (img, aud, dur) in enumerate(segments):
        seg_file = os.path.join(FRAMES_DIR, f"seg_{i:04d}.mp4")
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1', '-i', os.path.abspath(img).replace('\\', '/'),
            '-i', os.path.abspath(aud).replace('\\', '/'),
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-tune', 'stillimage',
            '-c:a', 'aac', '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            '-t', str(round(dur, 2)),
            '-shortest', '-r', '24',
            seg_file
        ]
        subprocess.run(cmd, capture_output=True, timeout=60)
        seg_files.append(seg_file)
        if (i + 1) % 30 == 0:
            print(f"   ... rendered {i + 1}/{len(segments)} segments")

    # Concatenate
    print("\n[3/3] Joining all segments...")
    concat_file = os.path.join(FRAMES_DIR, "concat.txt")
    with open(concat_file, 'w') as f:
        for sf in seg_files:
            f.write(f"file '{os.path.abspath(sf).replace(chr(92), '/')}'\n")

    result = subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file,
        '-c', 'copy', OUTPUT_FILE
    ], capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr[-500:]}")
        return

    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print(f"DONE! Video: {OUTPUT_FILE}")
    print(f"Size: {size_mb:.1f} MB | Duration: {int(total_dur)//60}m {int(total_dur)%60}s")
    print(f"{'=' * 60}")

    # Cleanup segment files (keep frames in case of re-runs)
    for sf in seg_files:
        if os.path.exists(sf):
            os.remove(sf)
    if os.path.exists(concat_file):
        os.remove(concat_file)
    for f in os.listdir(FRAMES_DIR):
        if f.endswith('.png'):
            os.remove(os.path.join(FRAMES_DIR, f))


if __name__ == "__main__":
    main()
