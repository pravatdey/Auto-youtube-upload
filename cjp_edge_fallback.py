# -*- coding: utf-8 -*-
"""
Fallback: generate any missing CJP narration clips using edge-tts (free, no quota).
Used when Gemini TTS hits its daily quota. Saves into output/cjp_audio/.
"""
import asyncio
import os

import edge_tts

from cjp_content import SECTIONS

OUTPUT_DIR = "output/cjp_audio"
VOICE = "hi-IN-MadhurNeural"  # Hindi male voice, closest to the Gemini "Charon" tone
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def synth(text, path):
    communicate = edge_tts.Communicate(text, VOICE, rate="-6%")
    await communicate.save(path)


def main():
    missing = []
    for s in SECTIONS:
        path = os.path.join(OUTPUT_DIR, f"{s['key']}.mp3")
        if not (os.path.exists(path) and os.path.getsize(path) > 1000):
            missing.append((s["key"], s["narration"], path))

    if not missing:
        print("No missing clips. Nothing to do.")
        return

    print(f"edge-tts fallback: generating {len(missing)} missing clip(s) "
          f"with voice {VOICE}")
    for key, text, path in missing:
        print(f"  -> {key} ({len(text)} chars)...")
        asyncio.run(synth(text, path))
        print(f"     OK ({os.path.getsize(path)/1024:.0f} KB)")
    print("Done.")


if __name__ == "__main__":
    main()
