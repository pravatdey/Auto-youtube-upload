"""
Generate all Hindi audio clips for OPSC OCS video using Gemini TTS.
Saves clips as MP3 files in output/audio_gemini/ directory.

NOTE: Free tier rate limits ~3-10 requests/minute for gemini-2.5-flash-preview-tts.
Script handles retries and throttling automatically.
"""
import os
import time
import wave
import io
import sys
from google import genai
from google.genai import types
from google.api_core import exceptions
from dotenv import load_dotenv
from pydub import AudioSegment

from hindi_narrations import HINDI_NARRATIONS

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env")
    sys.exit(1)

client = genai.Client(api_key=API_KEY)

# Config
MODEL = "gemini-3.1-flash-tts-preview"  # Newer model with better free-tier limits
VOICE_NAME = "Charon"  # Deep, professional male voice good for narration
OUTPUT_DIR = "output/audio_gemini"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Rate limiting - free tier strict (~10 RPM, 200 RPD)
INITIAL_DELAY = 7  # seconds between requests (~8 RPM safe)
MAX_RETRIES = 10  # more retries since free tier hits limits frequently

# Daily request budget - leave headroom under 200 RPD free tier limit
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "150"))  # override via env var

# Section + intro/outro narrations
INTRO_TEXT = "OPSC OCS प्रीलिम्स 2024 के कंप्लीट सॉल्यूशन वीडियो में आपका स्वागत है। इस वीडियो में हम पेपर 1 जनरल स्टडीज के सभी 100 प्रश्नों को विस्तृत व्याख्या के साथ हल करेंगे। तो चलिए शुरू करते हैं!"
OUTRO_TEXT = "OPSC OCS प्रीलिम्स 2024 पेपर 1 के सभी 100 प्रश्न पूरे हुए। अगर यह वीडियो आपके लिए उपयोगी रही तो कृपया लाइक, शेयर और सब्सक्राइब करें। अपना स्कोर नीचे कमेंट में बताएं। आपकी तैयारी के लिए शुभकामनाएं!"
SECTION_TEXTS = [
    "सेक्शन 1. राजनीति, इतिहास और शासन। प्रश्न 1 से 25।",
    "सेक्शन 2. भूगोल, अर्थव्यवस्था और पर्यावरण। प्रश्न 26 से 50।",
    "सेक्शन 3. विज्ञान, प्रौद्योगिकी और करेंट अफेयर्स। प्रश्न 51 से 75।",
    "सेक्शन 4. ओडिशा विशेष और विविध। प्रश्न 76 से 100।"
]


def pcm_to_mp3(pcm_data, output_path, sample_rate=24000):
    """Convert raw PCM bytes to MP3 file."""
    audio = AudioSegment(
        data=pcm_data,
        sample_width=2,  # 16-bit
        frame_rate=sample_rate,
        channels=1
    )
    audio.export(output_path, format="mp3", bitrate="128k")


def generate_audio(text, output_path, retries=MAX_RETRIES):
    """Generate audio with retries and exponential backoff."""
    if os.path.exists(output_path):
        return True  # Already exists, skip

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=text,
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

        except exceptions.ResourceExhausted as e:
            # Free tier - longer waits when rate-limited
            wait = min(60 * (attempt + 1), 300)  # 60s, 120s, 180s, 240s, 300s, 300s...
            print(f"   Rate limit hit. Waiting {wait}s before retry {attempt + 1}/{retries}...")
            time.sleep(wait)

        except Exception as e:
            err_msg = str(e)
            if "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower() or "429" in err_msg:
                wait = min(60 * (attempt + 1), 300)
                print(f"   Quota error. Waiting {wait}s before retry {attempt + 1}/{retries}...")
                time.sleep(wait)
            else:
                print(f"   Error: {err_msg[:200]}. Retrying in 15s...")
                time.sleep(15)

    print(f"   FAILED after {retries} retries: {output_path}")
    return False


def main():
    print("=" * 60)
    print("GEMINI TTS - Hindi Audio Generation")
    print(f"Voice: {VOICE_NAME} | Model: {MODEL}")
    print("=" * 60)

    # Build task list
    tasks = []
    tasks.append(("intro", INTRO_TEXT, os.path.join(OUTPUT_DIR, "intro.mp3")))
    for i, st in enumerate(SECTION_TEXTS):
        tasks.append((f"section_{i}", st, os.path.join(OUTPUT_DIR, f"section_{i}.mp3")))
    for q_no in sorted(HINDI_NARRATIONS.keys()):
        q_text, a_text = HINDI_NARRATIONS[q_no]
        tasks.append((f"q_{q_no}", q_text, os.path.join(OUTPUT_DIR, f"q_{q_no:03d}.mp3")))
        tasks.append((f"a_{q_no}", a_text, os.path.join(OUTPUT_DIR, f"a_{q_no:03d}.mp3")))
    tasks.append(("outro", OUTRO_TEXT, os.path.join(OUTPUT_DIR, "outro.mp3")))

    # Filter out already-generated
    pending = [t for t in tasks if not os.path.exists(t[2])]
    done = len(tasks) - len(pending)

    print(f"\nTotal clips: {len(tasks)}")
    print(f"Already done: {done}")
    print(f"Pending: {len(pending)}")
    print(f"Daily limit: {DAILY_LIMIT} requests")

    # Cap today's run at DAILY_LIMIT requests
    today_batch = pending[:DAILY_LIMIT]
    deferred = pending[DAILY_LIMIT:]
    print(f"Today's batch: {len(today_batch)} clips")
    print(f"Deferred to next run: {len(deferred)} clips")
    print(f"Estimated time: {len(today_batch) * INITIAL_DELAY // 60}m {len(today_batch) * INITIAL_DELAY % 60}s\n")

    if not today_batch:
        print("All audio clips already generated!")
        return

    start_time = time.time()
    success_count = 0
    fail_count = 0

    for i, (name, text, output_path) in enumerate(today_batch):
        elapsed = time.time() - start_time
        eta = (elapsed / max(i, 1)) * (len(today_batch) - i) if i > 0 else 0
        print(f"[{i+1}/{len(today_batch)}] Generating {name}... (elapsed: {int(elapsed)}s, ETA: {int(eta)}s)")

        if generate_audio(text, output_path):
            success_count += 1
            size_kb = os.path.getsize(output_path) / 1024
            print(f"   OK ({size_kb:.0f} KB)")
        else:
            fail_count += 1

        # Throttle to avoid hitting rate limits
        time.sleep(INITIAL_DELAY)

    print(f"\n{'=' * 60}")
    print(f"DONE - Success: {success_count}, Failed: {fail_count}")
    print(f"Total time: {int(time.time() - start_time)}s")
    if deferred:
        print(f"\n>>> {len(deferred)} clips deferred to tomorrow's run.")
        print(f">>> Run this script again tomorrow to continue.")
    else:
        print(f"\n>>> ALL CLIPS GENERATED! Run render_video_gemini.py next.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
