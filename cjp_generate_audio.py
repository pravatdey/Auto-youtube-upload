# -*- coding: utf-8 -*-
"""
Generate Hindi narration audio for the Cockroach Janta Party video using Gemini TTS.

12 longer clips (one per section) -> fewer API calls, safer on free-tier rate limits.
Saves MP3 files to output/cjp_audio/.
"""
import os
import sys
import time

from google import genai
from google.genai import types
from google.api_core import exceptions
from dotenv import load_dotenv
from pydub import AudioSegment

from cjp_content import SECTIONS

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env")
    sys.exit(1)

client = genai.Client(api_key=API_KEY)

# Model + voice. Charon = deep, professional male voice good for narration.
MODEL = "gemini-2.5-flash-preview-tts"
VOICE_NAME = "Charon"
OUTPUT_DIR = "output/cjp_audio"
os.makedirs(OUTPUT_DIR, exist_ok=True)

INITIAL_DELAY = 8   # seconds between requests (~7-8 RPM, safe for free tier)
MAX_RETRIES = 10

# Light Hindi-narration style hint prepended to each clip request
STYLE_PREFIX = (
    "एक स्पष्ट, आत्मविश्वासी और आकर्षक समाचार-शैली में हिंदी में पढ़ें: "
)


def pcm_to_mp3(pcm_data, output_path, sample_rate=24000):
    audio = AudioSegment(
        data=pcm_data, sample_width=2, frame_rate=sample_rate, channels=1
    )
    audio.export(output_path, format="mp3", bitrate="160k")


def generate_audio(text, output_path, retries=MAX_RETRIES):
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return True  # already done

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=STYLE_PREFIX + text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=VOICE_NAME,
                            )
                        )
                    ),
                ),
            )
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            pcm_to_mp3(audio_data, output_path)
            return True

        except exceptions.ResourceExhausted:
            wait = min(60 * (attempt + 1), 300)
            print(f"   Rate limit. Waiting {wait}s (retry {attempt+1}/{retries})...")
            time.sleep(wait)

        except Exception as e:
            msg = str(e)
            if any(k in msg.upper() for k in ("RESOURCE_EXHAUSTED", "QUOTA", "429")):
                wait = min(60 * (attempt + 1), 300)
                print(f"   Quota error. Waiting {wait}s (retry {attempt+1}/{retries})...")
                time.sleep(wait)
            else:
                print(f"   Error: {msg[:200]}. Retry in 15s...")
                time.sleep(15)

    print(f"   FAILED after {retries} retries: {output_path}")
    return False


def main():
    print("=" * 60)
    print("GEMINI TTS - Cockroach Janta Party (Hindi narration)")
    print(f"Voice: {VOICE_NAME} | Model: {MODEL}")
    print("=" * 60)

    tasks = [
        (s["key"], s["narration"], os.path.join(OUTPUT_DIR, f"{s['key']}.mp3"))
        for s in SECTIONS
    ]
    pending = [t for t in tasks if not (os.path.exists(t[2]) and os.path.getsize(t[2]) > 1000)]
    print(f"\nTotal clips: {len(tasks)} | Already done: {len(tasks)-len(pending)} | Pending: {len(pending)}")
    if not pending:
        print("All audio clips already generated!")
        return

    start = time.time()
    ok = fail = 0
    for i, (name, text, path) in enumerate(pending):
        print(f"[{i+1}/{len(pending)}] Generating {name} ({len(text)} chars)...")
        if generate_audio(text, path):
            ok += 1
            print(f"   OK ({os.path.getsize(path)/1024:.0f} KB)")
        else:
            fail += 1
        if i < len(pending) - 1:
            time.sleep(INITIAL_DELAY)

    print("=" * 60)
    print(f"DONE - Success: {ok}, Failed: {fail} | Time: {int(time.time()-start)}s")
    if fail:
        print(">>> Some clips failed. Re-run this script to retry the missing ones.")
    else:
        print(">>> All clips generated. Run cjp_build_video.py next.")
    print("=" * 60)


if __name__ == "__main__":
    main()
