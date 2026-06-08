"""Create a ~15-min Hindi tech current-affairs video for UPSC / civil services prep.

Topic: Current technology developments in the world (India + Global round-up),
grounded on real, researched June-2026 facts so the narration is accurate
instead of hallucinated.

Pipeline (reuses helpers from create_news_video.py):
  1. Generate a Hindi script via GitHub Models (GPT-4o), grounded on RESEARCH_FACTS
  2. Generate Hindi narration via edge-tts (hi-IN-SwaraNeural)
  3. Download real images per section (Bing/Wikimedia)
  4. Assemble slideshow video + watermark
  5. Create thumbnail + save upload metadata

Run:
    python create_tech_video.py
The channel intro is prepended separately by prepend_intro.py afterwards.
"""

import json
import os
import re
import sys
import time

from dotenv import load_dotenv

# Reuse the proven helpers from the existing news pipeline.
import create_news_video as nv

load_dotenv()

# ------------------------------------------------------------------
# Use a Devanagari-capable font for Hindi text overlays.
# ------------------------------------------------------------------
HINDI_FONT = "assets/fonts/Nirmala.ttc"
nv.FONT_PATH = HINDI_FONT  # PIL overlays + FFmpeg drawtext use this

VOICE = "hi-IN-SwaraNeural"
TARGET_MINUTES = 15
OUTPUT_DIR = "D:/temp"
TEMP_DIR = "D:/temp/tech_video_temp"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "World_Technology_CurrentAffairs_Hindi.mp4")

TOPIC = "Current Technology Developments in the World — India & Global Round-up (2026)"

# ------------------------------------------------------------------
# Researched, real facts (June 2026) used to GROUND the model so it
# does not invent numbers. Sourced from web research during creation.
# ------------------------------------------------------------------
RESEARCH_FACTS = """
=== INDIA — SEMICONDUCTORS ===
- India Semiconductor Mission (ISM) total outlay: Rs 76,000 crore.
- Union Budget 2026-27 announced India Semiconductor Mission 2.0 with Rs 1,000 crore for research, training and workforce.
- As of Dec 2025: 10 projects approved across 6 states, cumulative investment Rs 1.60 lakh crore.
- "Vikram 3201" processor developed by Semiconductor Laboratory (SCL), Mohali with ISRO — India's own space-grade chip.

=== INDIA — DEFENCE / DRDO ===
- "Prajna" — AI-powered satellite imaging & analytics system by DRDO's lab CAIR (Centre for AI and Robotics) for surveillance and faster threat detection.
- DRDO launched a DARPA-style deep-tech initiative: Technology Development Fund financing 5 deep-tech projects (quantum, blockchain, AI for military), up to Rs 50 crore each.
- DRDO work spans missile propulsion, precision-guided weapons, military logistics, and supporting Gaganyaan.

=== INDIA — SPACE / ISRO ===
- Gaganyaan-1 (uncrewed) scheduled for H2 2026; carries half-humanoid robot "Vyommitra"; Vyommitra integration began 28 April 2026.
- 8000+ ground tests completed by early 2026; first Integrated Air Drop Test (IADT-01) done 24 Aug 2025 with a ~4.8-tonne dummy crew capsule dropped from ~3 km by an IAF Chinook.
- Bharatiya Antariksh Station (BAS): BAS-1 module and further missions targeted by 2028; aims at long-duration human spaceflight.
- Chandrayaan-4: sample-return mission from the Moon's south pole; will use SpaDeX docking tech demonstrated in early 2025.

=== INDIA — AI POLICY ===
- India to host the "AI Impact Summit 2026" focused on democratisation of AI — expanding access to technology and skills.

=== GLOBAL — AI & CHIPS ===
- 2026's tightest constraint for AI firms is the production of AI chips themselves.
- NVIDIA redirected TSMC capacity (from H200 for China) to next-gen "Vera Rubin" chips with confirmed orders from OpenAI, Google.
- High Bandwidth Memory (HBM) revenue ~USD 34 billion, roughly doubling.
- China / Huawei scaling domestic "Ascend" AI chips: Ascend 910C target ~600,000 units in 2026; Ascend 950PR ~750,000 units.
- OpenAI committed ~USD 100 billion to an AWS Trainium cloud deal (2 GW compute); Cerebras signed a USD 20B+ deal for up to 750MW inference capacity.
- US export controls remain the central lever in the US-China AI race.

=== GLOBAL — QUANTUM ===
- Quantum tech described as reaching its "transistor moment" — moving from lab to practical deployment.
- China's new Five-Year Plan explicitly targets scalable quantum computers and an integrated space-earth quantum communication network.
- 2026 priority: post-quantum cybersecurity — defending against future cryptographically-relevant quantum computers ("harvest now, decrypt later").

=== GLOBAL — SPACE / CONNECTIVITY ===
- Continued surge in Low Earth Orbit (LEO) satellite launches for truly global connectivity.
"""

# Section blueprint so we get good UPSC coverage at ~15 min (18-20 sections).
SECTION_BLUEPRINT = """
1. Introduction — why technology current-affairs matters for UPSC Prelims & Mains (GS Paper 3 Science & Tech)
2. The big picture: the world's 2026 tech landscape at a glance
3. India Semiconductor Mission (ISM) — outlay, ISM 2.0, why chips = strategic autonomy
4. Vikram 3201 — India's space-grade processor (SCL Mohali + ISRO)
5. Global AI chip race — Nvidia, TSMC, Vera Rubin, the compute bottleneck
6. China's domestic chips — Huawei Ascend & the US export-control battle
7. High Bandwidth Memory (HBM) and the economics of AI infrastructure
8. DRDO 'Prajna' — AI for satellite surveillance & national security
9. DRDO's DARPA-style deep-tech fund — quantum, blockchain, AI for defence
10. Gaganyaan-1 & Vyommitra — India's human spaceflight roadmap
11. Bharatiya Antariksh Station (BAS) — India's own space station plan
12. Chandrayaan-4 — Moon sample-return and SpaDeX docking tech
13. Quantum computing's 'transistor moment' — lab to deployment
14. Post-quantum cybersecurity — 'harvest now, decrypt later' threat
15. China's Five-Year Plan — quantum + space-earth quantum communication
16. LEO satellites & global connectivity boom
17. India's AI Impact Summit 2026 — democratising AI
18. UPSC angle — how to write/answer these in Prelims & Mains, key terms to remember
19. Conclusion — quick recap + subscribe call-to-action
"""

GITHUB_MODELS_BASE = nv.GITHUB_MODELS_BASE
GITHUB_MODEL = nv.GITHUB_MODEL


def generate_hindi_script(target_minutes: int = TARGET_MINUTES) -> dict:
    """Generate a Hindi UPSC tech script grounded on RESEARCH_FACTS."""
    from openai import OpenAI

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not set in environment (.env).")
        sys.exit(1)

    client = OpenAI(base_url=GITHUB_MODELS_BASE, api_key=token)

    # Hindi tokenizes ~3-4x heavier than English, so a single call for 18-19
    # long sections overflows max_tokens and truncates the JSON. Generate the
    # sections in small batches, then a tiny final call for title/desc/tags.
    blueprint_lines = [ln.strip() for ln in SECTION_BLUEPRINT.strip().splitlines() if ln.strip()]
    BATCH = 5
    batches = [blueprint_lines[i:i + BATCH] for i in range(0, len(blueprint_lines), BATCH)]

    print(f"Generating Hindi script in {len(batches)} batches "
          f"({len(blueprint_lines)} sections, grounded on researched facts)...")

    all_sections = []
    for bi, batch in enumerate(batches):
        batch_spec = "\n".join(batch)
        prompt = f"""You are an expert Hindi scriptwriter for a top UPSC / civil-services current-affairs YouTube channel.

Write part of a {target_minutes}-minute HINDI (Devanagari) video script on CURRENT WORLD TECHNOLOGY DEVELOPMENTS (India + Global) for UPSC / civil-services prep.

Base EVERY fact, number, name and date ONLY on the GROUNDING FACTS. Do NOT invent statistics; if a detail is absent, speak generally instead of fabricating.

=== GROUNDING FACTS ===
{RESEARCH_FACTS}

Write ONLY these sections, in this exact order:
{batch_spec}

Return ONLY a JSON ARRAY (no wrapper object, no markdown) where each element is:
{{
    "heading": "Short Hindi heading (keep proper nouns like Gaganyaan, DRDO, Nvidia as-is)",
    "narration": "230-320 words of natural conversational Hindi, exam-focused, using the real numbers/names from the facts",
    "image_search_query": "SPECIFIC ENGLISH photo search query likely to return a real photo (e.g. 'ISRO Gaganyaan crew module', 'semiconductor fabrication clean room')",
    "key_points": ["3-4 SHORT Hindi bullets, each under ~7 words"]
}}

Return ONLY the JSON array."""

        resp = client.chat.completions.create(
            model=GITHUB_MODEL,
            messages=[
                {"role": "system", "content": "You are a Hindi UPSC scriptwriter. Return only a valid JSON array, no markdown. Stay strictly accurate to the grounding facts."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=8000,
        )
        secs = _parse_sections_array(resp.choices[0].message.content.strip())
        print(f"  Batch {bi + 1}/{len(batches)}: {len(secs)} sections")
        all_sections.extend(secs)

    if not all_sections:
        raise RuntimeError("No sections generated.")

    # Small, cheap call for the metadata (title/description/tags/thumbnail).
    headings = "; ".join(s.get("heading", "") for s in all_sections)
    meta_prompt = f"""For a Hindi UPSC current-affairs video covering these sections: {headings}

Return ONLY this JSON object (no markdown):
{{
  "title": "Hindi catchy SEO YouTube title under 90 chars (may include 'UPSC')",
  "description": "Hindi YouTube description, 3 short paragraphs with exam relevance and hashtags",
  "tags": ["15+ tags, mix Hindi + English UPSC keywords"],
  "thumbnail_text": "max 5 words, Hindi or English"
}}"""
    meta_resp = client.chat.completions.create(
        model=GITHUB_MODEL,
        messages=[
            {"role": "system", "content": "Return only a valid JSON object, no markdown."},
            {"role": "user", "content": meta_prompt},
        ],
        temperature=0.6,
        max_tokens=1500,
    )
    try:
        meta = _parse_json_lenient(meta_resp.choices[0].message.content.strip())
    except Exception:
        meta = {}

    script = {
        "title": meta.get("title", "टेक्नोलॉजी करेंट अफेयर्स 2026 — UPSC"),
        "description": meta.get("description", ""),
        "tags": meta.get("tags", []),
        "thumbnail_text": meta.get("thumbnail_text", "Tech Current Affairs"),
        "sections": all_sections,
    }
    print(f"  Generated {len(script['sections'])} sections total")
    print(f"  Title: {script['title']}")
    return script


def _parse_sections_array(content: str) -> list:
    """Parse a JSON array of section objects, tolerating fences/defects."""
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    content = content.strip()
    start, end = content.find("["), content.rfind("]")
    if start != -1 and end != -1 and end > start:
        candidate = content[start:end + 1]
    else:
        candidate = content
    for attempt in (candidate, re.sub(r",(\s*[}\]])", r"\1", candidate)):
        try:
            data = json.loads(attempt)
            if isinstance(data, list):
                return [s for s in data if isinstance(s, dict) and s.get("narration")]
        except json.JSONDecodeError:
            continue
    # Salvage individual objects.
    out = []
    for blob in re.findall(r"\{[^{}]*?\"narration\"[^{}]*?\}", candidate, re.DOTALL):
        try:
            out.append(json.loads(re.sub(r",(\s*})", r"\1", blob)))
        except json.JSONDecodeError:
            continue
    return out


def _parse_json_lenient(content: str) -> dict:
    """Parse model JSON output, tolerating fences and minor defects."""
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    content = content.strip()

    # Trim to the outermost { ... } in case of stray prose.
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end != -1 and end > start:
        content = content[start:end + 1]

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Repair common defects: trailing commas, stray control chars.
    repaired = re.sub(r",(\s*[}\]])", r"\1", content)
    repaired = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", repaired)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Last resort: salvage as many complete section objects as possible so a
    # single malformed section doesn't sink the whole render.
    try:
        title_m = re.search(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', content)
        title = title_m.group(1) if title_m else "Tech Current Affairs"
        sections = []
        for blob in re.findall(r"\{[^{}]*\"narration\"[^{}]*\}", content, re.DOTALL):
            try:
                sections.append(json.loads(re.sub(r",(\s*})", r"\1", blob)))
            except json.JSONDecodeError:
                continue
        if not sections:
            raise ValueError("no salvageable sections")
        print(f"  WARNING: JSON was malformed; salvaged {len(sections)} sections.")
        return {"title": title, "description": "", "tags": [],
                "thumbnail_text": "Tech Current Affairs", "sections": sections}
    except Exception as e:
        # Dump raw output for debugging before giving up.
        dump = os.path.join(TEMP_DIR, "raw_model_output.txt")
        os.makedirs(TEMP_DIR, exist_ok=True)
        with open(dump, "w", encoding="utf-8") as f:
            f.write(content)
        raise RuntimeError(f"Could not parse model JSON ({e}). Raw saved to {dump}")


def create_tech_thumbnail(title: str, thumbnail_text: str, output_path: str):
    """Simple tech-themed thumbnail (avoids the India-SK specific one in nv)."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1280, 720))
    draw = ImageDraw.Draw(img)
    # Dark tech gradient (deep blue -> teal)
    for y in range(720):
        ratio = y / 720
        r = int(8 + ratio * 10)
        g = int(18 + ratio * 60)
        b = int(45 + ratio * 90)
        draw.line([(0, y), (1280, y)], fill=(r, g, b))

    # Accent bars
    draw.rectangle([0, 0, 1280, 10], fill=(0, 220, 200))
    draw.rectangle([0, 710, 1280, 720], fill=(0, 220, 200))
    # India tricolor stripe on left
    draw.rectangle([0, 60, 22, 240], fill=(255, 153, 51))
    draw.rectangle([0, 240, 22, 420], fill=(255, 255, 255))
    draw.rectangle([0, 420, 22, 600], fill=(19, 136, 8))

    try:
        font_big = ImageFont.truetype(HINDI_FONT, 88)
        font_med = ImageFont.truetype(HINDI_FONT, 52)
        font_small = ImageFont.truetype(HINDI_FONT, 38)
    except (OSError, IOError):
        font_big = font_med = font_small = ImageFont.load_default()

    tt = (thumbnail_text or "Tech Current Affairs").strip()
    y = 130
    for line in [tt[:18], tt[18:36]] if len(tt) > 18 else [tt]:
        if not line:
            continue
        draw.text((62, y + 3), line, fill=(0, 0, 0), font=font_big)
        draw.text((60, y), line, fill=(255, 220, 0), font=font_big)
        y += 110

    draw.rectangle([60, y + 10, 760, y + 16], fill=(0, 220, 200))
    y += 50
    draw.text((62, y + 2), "AI • Chips • Space • Quantum", fill=(0, 0, 0), font=font_med)
    draw.text((60, y), "AI • Chips • Space • Quantum", fill=(180, 240, 255), font=font_med)

    # Bottom branding
    draw.text((60, 645), "UPSC / Civil Services Current Affairs", fill=(255, 220, 100), font=font_small)

    try:
        if os.path.isfile(nv.WATERMARK):
            wm = Image.open(nv.WATERMARK).convert("RGBA").resize((150, 150), Image.LANCZOS)
            img.paste(wm, (1280 - 200, 40), wm)
    except Exception:
        pass

    img.save(output_path, quality=95)
    print(f"  Thumbnail saved: {output_path}")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(TEMP_DIR, exist_ok=True)

    script_cache = os.path.join(TEMP_DIR, "script_hindi.json")
    thumbnail_path = OUTPUT_PATH.replace(".mp4", "_thumbnail.jpg")

    print("=" * 64)
    print("  AI HINDI TECH CURRENT-AFFAIRS VIDEO CREATOR (UPSC)")
    print("=" * 64)
    print(f"  Topic:    {TOPIC}")
    print(f"  Voice:    {VOICE}")
    print(f"  Font:     {HINDI_FONT}")
    print(f"  Output:   {OUTPUT_PATH}")
    print("=" * 64)

    start = time.time()

    # STEP 1: Script (cache so we don't re-burn API quota on reruns)
    print("\n[1/5] Generating Hindi script...")
    if os.path.isfile(script_cache):
        with open(script_cache, "r", encoding="utf-8") as f:
            script = json.load(f)
        print(f"  Loaded cached script ({len(script['sections'])} sections)")
    else:
        script = generate_hindi_script()
        with open(script_cache, "w", encoding="utf-8") as f:
            json.dump(script, f, indent=2, ensure_ascii=False)
        print(f"  Cached -> {script_cache}")

    # STEP 2: Narration (Hindi)
    print(f"\n[2/5] Generating Hindi narration ({VOICE})...")
    audio_files = nv.generate_narration(script["sections"], VOICE, TEMP_DIR)
    print(f"  {len(audio_files)} audio segments")

    # STEP 3: Images
    print("\n[3/5] Downloading images / building slides...")
    image_files = nv.download_images(script["sections"], TEMP_DIR)
    print(f"  {len(image_files)} slides")

    # STEP 4: Assemble
    print("\n[4/5] Assembling video...")
    nv.assemble_video(image_files, audio_files, script["sections"],
                      OUTPUT_PATH, nv.WATERMARK)

    # STEP 5: Thumbnail
    print("\n[5/5] Creating thumbnail...")
    create_tech_thumbnail(script["title"], script.get("thumbnail_text", ""), thumbnail_path)

    elapsed = time.time() - start
    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024) if os.path.isfile(OUTPUT_PATH) else 0
    print("\n" + "=" * 64)
    print("  BASE VIDEO CREATED (intro not yet added)")
    print("=" * 64)
    print(f"  Video:     {OUTPUT_PATH} ({size_mb:.1f} MB)")
    print(f"  Thumbnail: {thumbnail_path}")
    print(f"  Title:     {script['title']}")
    print(f"  Time:      {elapsed/60:.1f} min")
    print("=" * 64)

    metadata = {
        "video_path": OUTPUT_PATH,
        "thumbnail_path": thumbnail_path,
        "title": script["title"],
        "description": script.get("description", ""),
        "tags": script.get("tags", []),
        "category_id": "27",
        "privacy": "private",  # safe default; user verifies before going public
    }
    with open(OUTPUT_PATH.replace(".mp4", "_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print("  Metadata saved (for upload after your verification).")


if __name__ == "__main__":
    main()
