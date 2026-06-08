"""Generate topic-wise short notes from video audio using Whisper.

Extracts audio in chunks, transcribes with Whisper, then organizes
into topic-wise bullet-point notes.

Usage:
    python -m pipeline.notes "C:/Users/PravatkumarDey/Downloads/Complete Modern Indian History.mp4"
    python -m pipeline.notes "video.mp4" --model base --chunk 600
"""

import argparse
import os
import subprocess
import sys
import time
import json

import whisper


def extract_audio_chunk(video_path: str, output_path: str,
                        start_sec: float, duration_sec: float):
    """Extract a chunk of audio from video as WAV (16kHz mono for Whisper)."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_sec),
        "-t", str(duration_sec),
        "-i", video_path,
        "-vn",                    # No video
        "-ar", "16000",           # 16kHz sample rate (Whisper expects this)
        "-ac", "1",               # Mono
        "-c:a", "pcm_s16le",      # 16-bit PCM WAV
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr[-200:]}")


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip()) if result.stdout.strip() else 0


def format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def generate_notes(video_path: str, output_path: str,
                   model_name: str = "base",
                   chunk_duration: int = 600,
                   language: str = "en",
                   skip_start: float = 0,
                   skip_end: float = 0,
                   watermark_path: str = "assets/watermark.png"):
    """Generate topic-wise notes from a video.

    Args:
        video_path: Path to video file
        output_path: Path for output notes file (.md)
        model_name: Whisper model (tiny/base/small/medium/large)
        chunk_duration: Audio chunk size in seconds (default 600 = 10 min)
        language: Language code (default "en")
        skip_start: Skip first N seconds (intro)
        skip_end: Skip last N seconds (outro/promo)
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    duration = get_video_duration(video_path)
    effective_start = skip_start
    effective_end = duration - skip_end if skip_end > 0 else duration
    effective_duration = effective_end - effective_start

    print("=" * 60)
    print("GENERATING NOTES FROM VIDEO")
    print("=" * 60)
    print(f"Video:    {video_path}")
    print(f"Duration: {format_time(duration)} ({duration:.0f}s)")
    print(f"Content:  {format_time(effective_start)} to {format_time(effective_end)}")
    print(f"Model:    {model_name}")
    print(f"Chunk:    {chunk_duration}s ({chunk_duration // 60} min)")
    print()

    # Load Whisper model
    print(f"Loading Whisper '{model_name}' model...")
    model = whisper.load_model(model_name)
    print("Model loaded.\n")

    temp_dir = os.path.dirname(output_path) or "."
    temp_audio = os.path.join(temp_dir, "_temp_chunk.wav")

    # Process in chunks — with resume support
    num_chunks = int(effective_duration / chunk_duration) + 1
    all_segments = []

    # Check for existing partial transcript to resume from
    transcript_path = output_path.replace(".md", "_transcript.json")
    resume_from = 0
    if os.path.isfile(transcript_path):
        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                all_segments = json.load(f)
            if all_segments:
                last_end = max(seg["end"] for seg in all_segments)
                resume_from = int((last_end - effective_start) / chunk_duration)
                print(f"RESUMING from chunk {resume_from + 1}/{num_chunks} "
                      f"({len(all_segments)} segments already done)\n")
        except (json.JSONDecodeError, KeyError):
            all_segments = []

    start_time = time.time()

    for i in range(resume_from, num_chunks):
        chunk_start = effective_start + i * chunk_duration
        chunk_end = min(chunk_start + chunk_duration, effective_end)
        actual_duration = chunk_end - chunk_start

        if actual_duration <= 1:
            break

        pct = (i + 1) / num_chunks * 100
        print(f"[{pct:5.1f}%] Chunk {i + 1}/{num_chunks}: "
              f"{format_time(chunk_start)} - {format_time(chunk_end)}")

        # Extract audio chunk
        extract_audio_chunk(video_path, temp_audio, chunk_start, actual_duration)

        # Transcribe
        result = model.transcribe(
            temp_audio,
            language=language,
            task="transcribe",
            verbose=False,
        )

        text = result["text"].strip()
        if text:
            timestamp = format_time(chunk_start)
            all_segments.append({
                "start": chunk_start,
                "end": chunk_end,
                "timestamp": timestamp,
                "text": text,
            })

            # Print a preview (handle non-ASCII safely)
            preview = text[:100] + "..." if len(text) > 100 else text
            try:
                print(f"         {preview}")
            except UnicodeEncodeError:
                print(f"         [transcribed {len(text)} chars]")

        # Save progress after each chunk (for resume)
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(all_segments, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start_time
    print(f"\nTranscription done in {elapsed / 60:.1f} minutes")
    print(f"Total segments: {len(all_segments)}")

    # Clean up temp audio
    if os.path.isfile(temp_audio):
        os.remove(temp_audio)

    # Save raw transcript (already saved per-chunk, but final save here)
    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(all_segments, f, indent=2, ensure_ascii=False)
    print(f"Raw transcript saved: {transcript_path}")

    # Generate PDF notes
    pdf_path = output_path.replace(".md", ".pdf")
    print("\nGenerating UPSC-style PDF notes...")
    _build_upsc_pdf(all_segments, video_path, pdf_path, watermark_path)

    # Also save markdown version
    print("Generating markdown notes...")
    notes_md = _build_notes_markdown(all_segments, video_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(notes_md)

    print(f"\nNotes saved:")
    print(f"  PDF: {pdf_path}")
    print(f"  MD:  {output_path}")
    print(f"\n{'=' * 60}")
    print(f"DONE!")
    print(f"{'=' * 60}")


def _build_upsc_pdf(segments: list[dict], video_path: str,
                    pdf_path: str, watermark_path: str = None):
    """Build a professional UPSC-style PDF with watermark on first page."""
    from fpdf import FPDF

    video_name = os.path.splitext(os.path.basename(video_path))[0]
    title = video_name.replace("_", " ").replace("-", " ")

    # Clean non-latin characters from all segments for PDF compatibility
    def _clean_text(text):
        """Keep only characters that Helvetica/latin-1 can render."""
        cleaned = []
        for c in text:
            if ord(c) <= 255:  # latin-1 range
                cleaned.append(c)
            elif c in '\u2013\u2014\u2018\u2019\u201c\u201d\u2026':
                # Replace smart quotes/dashes with ASCII equivalents
                replacements = {'\u2013': '-', '\u2014': '-', '\u2018': "'",
                                '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2026': '...'}
                cleaned.append(replacements.get(c, ''))
            # Skip all other non-latin characters
        return "".join(cleaned).strip()

    class UPSCNotesPDF(FPDF):
        def header(self):
            if self.page_no() > 1:
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(100, 100, 100)
                self.cell(0, 8, f"{title} | Civil Services Exam Preparation", align="C")
                self.ln(5)
                # Header line
                self.set_draw_color(0, 51, 102)
                self.set_line_width(0.5)
                self.line(10, 13, 200, 13)
                self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    pdf = UPSCNotesPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ===================== COVER PAGE =====================
    pdf.add_page()

    # Watermark logo on cover page
    if watermark_path and os.path.isfile(watermark_path):
        # Center the logo at top
        pdf.image(watermark_path, x=65, y=20, w=80)
        y_after_logo = 110
    else:
        y_after_logo = 40

    # Title
    pdf.set_y(y_after_logo)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(0, 51, 102)  # Dark blue
    pdf.multi_cell(0, 14, title, align="C")
    pdf.ln(8)

    # Subtitle
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(180, 0, 0)  # Dark red
    pdf.cell(0, 10, "UPSC Civil Services Exam Preparation", align="C")
    pdf.ln(15)

    # Decorative line
    pdf.set_draw_color(0, 51, 102)
    pdf.set_line_width(1)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(10)

    # Info box
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 8, "Topic-wise Short Notes", align="C")
    pdf.ln(8)
    pdf.cell(0, 8, f"Total Segments: {len(segments)}", align="C")
    pdf.ln(8)

    total_dur = segments[-1]["end"] - segments[0]["start"] if segments else 0
    pdf.cell(0, 8, f"Content Duration: {format_time(total_dur)}", align="C")
    pdf.ln(15)

    # Subjects covered
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, "Relevant for:", align="C")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    for exam in ["UPSC CSE (Prelims & Mains)", "State PSC Examinations",
                  "SSC CGL / CHSL", "Other Competitive Exams"]:
        pdf.cell(0, 6, f">> {exam}", align="C")
        pdf.ln(6)

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 8, "Civil Services & Competitive Exam Prep", align="C")

    # ===================== TABLE OF CONTENTS =====================
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, "Table of Contents", align="C")
    pdf.ln(12)

    pdf.set_draw_color(0, 51, 102)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    for idx, seg in enumerate(segments, 1):
        timestamp = seg["timestamp"]
        clean = _clean_text(seg["text"])
        preview = clean[:60] + "..." if len(clean) > 60 else clean
        pdf.cell(15, 6, f"{idx}.", align="R")
        pdf.cell(25, 6, f"[{timestamp}]")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, preview)
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 10)
        if pdf.get_y() > 270:
            pdf.add_page()

    # ===================== NOTES CONTENT =====================
    for idx, seg in enumerate(segments, 1):
        timestamp = seg["timestamp"]
        text = _clean_text(seg["text"])

        # Section header
        if pdf.get_y() > 240:
            pdf.add_page()

        pdf.ln(4)

        # Section number + timestamp bar
        pdf.set_fill_color(0, 51, 102)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"  Section {idx}  |  [{timestamp}]", fill=True)
        pdf.ln(10)

        # Content as bullet points
        pdf.set_text_color(30, 30, 30)
        sentences = _split_sentences(text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            if pdf.get_y() > 265:
                pdf.add_page()

            # Bullet point
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(180, 0, 0)
            x_start = pdf.get_x()
            pdf.cell(8, 6, ">")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, sentence)
            pdf.ln(1)

        pdf.ln(3)

        # Light separator line between sections
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.3)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)

    # ===================== LAST PAGE =====================
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, "All the Best for Your Preparation!", align="C")
    pdf.ln(15)

    if watermark_path and os.path.isfile(watermark_path):
        pdf.image(watermark_path, x=75, y=pdf.get_y(), w=60)
        pdf.ln(65)

    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 8, "Civil Services & Competitive Exam Prep", align="C")
    pdf.ln(8)
    pdf.cell(0, 8, "Notes auto-generated using AI transcription", align="C")

    pdf.output(pdf_path)
    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    print(f"  PDF created: {pdf_path} ({size_mb:.1f} MB)")


def _build_notes_markdown(segments: list[dict], video_path: str) -> str:
    """Build organized markdown notes from transcript segments."""
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    lines = []
    lines.append(f"# {video_name} - UPSC Notes\n")
    lines.append("**Civil Services & Competitive Exam Preparation**\n")
    lines.append("---\n")

    for idx, seg in enumerate(segments, 1):
        timestamp = seg["timestamp"]
        text = seg["text"]

        lines.append(f"\n## Section {idx} [{timestamp}]\n")

        sentences = _split_sentences(text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:
                lines.append(f"- {sentence}")

        lines.append("")

    lines.append("\n---\n")
    lines.append("*Notes generated for UPSC Civil Services Exam Preparation*\n")

    return "\n".join(lines)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    import re
    sentences = re.split(r'(?<=[.?!])\s+', text)
    merged = []
    buffer = ""
    for s in sentences:
        if len(buffer) + len(s) < 30 and buffer:
            buffer += " " + s
        else:
            if buffer:
                merged.append(buffer)
            buffer = s
    if buffer:
        merged.append(buffer)
    return merged


def main():
    parser = argparse.ArgumentParser(
        description="Generate topic-wise notes from video using Whisper AI"
    )
    parser.add_argument("input", help="Input video path")
    parser.add_argument("-o", "--output", help="Output notes path (.md)")
    parser.add_argument("--model", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--chunk", type=int, default=600,
                        help="Audio chunk duration in seconds (default: 600 = 10 min)")
    parser.add_argument("--language", default="en",
                        help="Language code (default: en)")
    parser.add_argument("--skip-start", type=float, default=0,
                        help="Skip first N seconds (intro)")
    parser.add_argument("--skip-end", type=float, default=0,
                        help="Skip last N seconds (outro)")
    parser.add_argument("--watermark", default="assets/watermark.png",
                        help="Watermark logo for PDF cover page")

    args = parser.parse_args()

    if not args.output:
        base = os.path.splitext(args.input)[0]
        args.output = f"{base}_notes.md"

    generate_notes(
        video_path=args.input,
        output_path=args.output,
        model_name=args.model,
        chunk_duration=args.chunk,
        language=args.language,
        skip_start=args.skip_start,
        skip_end=args.skip_end,
        watermark_path=args.watermark,
    )


if __name__ == "__main__":
    main()
