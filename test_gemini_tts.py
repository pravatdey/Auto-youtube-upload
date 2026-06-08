"""Test Gemini TTS with a Hindi sample."""
import os
import wave
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
print(f"API Key loaded: {bool(API_KEY)}")

client = genai.Client(api_key=API_KEY)

text = "नमस्ते! यह OPSC OCS प्रीलिम्स 2024 का कंप्लीट सॉल्यूशन है। प्रश्न 1. लेखकों को उनकी पुस्तकों से मिलाइए।"

print("Generating Hindi audio with Gemini TTS...")

response = client.models.generate_content(
    model="gemini-2.5-flash-preview-tts",
    contents=text,
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Charon",  # Try Charon - good for narration
                )
            )
        ),
    ),
)

audio_data = response.candidates[0].content.parts[0].inline_data.data
print(f"Audio bytes: {len(audio_data)}")

# Save as WAV file (Gemini returns raw PCM)
output_path = "test_gemini_hindi.wav"
with wave.open(output_path, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)  # 16-bit
    wf.setframerate(24000)
    wf.writeframes(audio_data)

print(f"Saved to: {output_path}")
print(f"File size: {os.path.getsize(output_path)} bytes")
