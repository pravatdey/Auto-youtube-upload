"""Auto YouTube Upload Pipeline - CLI Entry Point.

Usage:
    python main.py process <video_path>         # Process video only (pitch + watermark)
    python main.py upload <video_or_dir>         # Upload to YouTube only
    python main.py run <video_path>              # Full pipeline: process + split + upload
"""

import argparse
import os
import sys

import yaml

from pipeline.processor import process_video
from pipeline.splitter import split_video
from uploader.auth import get_youtube_service
from uploader.youtube import upload_parts, upload_video


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    if not os.path.isfile(config_path):
        print(f"Warning: {config_path} not found, using defaults.")
        return {}
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


def cmd_process(args, config):
    """Handle the 'process' subcommand."""
    # Override config with CLI args
    if args.pitch is not None:
        config["pitch_shift"] = args.pitch
    if args.text is not None:
        config["watermark_text"] = args.text
    if args.remove_watermark is not None:
        config["remove_watermark"] = args.remove_watermark
    if args.blur_region is not None:
        config["blur_region"] = args.blur_region
    if args.crf is not None:
        config["crf"] = args.crf

    # Determine output path
    output = args.output
    if not output:
        base, ext = os.path.splitext(args.input)
        output = f"{base}_processed{ext}"

    processed = process_video(args.input, output, config, logo_path=args.logo)

    # Split if requested
    if args.split:
        duration = args.split_duration or config.get("split_duration", 900)
        output_dir = config.get("output_dir", "output")
        parts = split_video(processed, output_dir, duration)
        return parts

    return processed


def cmd_upload(args, config):
    """Handle the 'upload' subcommand."""
    service = get_youtube_service()

    privacy = args.privacy or config.get("default_privacy", "private")
    category = args.category or config.get("category_id", "22")
    tags = args.tags or config.get("default_tags", [])
    thumbnail = args.thumbnail or config.get("thumbnail_path")

    # Resolve playlist
    playlist_id = None
    playlist_name = args.playlist or config.get("playlist_name")
    if playlist_name:
        from uploader.playlist import get_or_create_playlist
        playlist_id = get_or_create_playlist(service, playlist_name, privacy)

    input_path = args.input

    if os.path.isdir(input_path):
        # Upload all video files in directory
        parts = sorted(
            os.path.join(input_path, f)
            for f in os.listdir(input_path)
            if f.endswith((".mp4", ".mkv", ".avi", ".mov"))
        )
        if not parts:
            print(f"No video files found in {input_path}")
            return

        title_template = args.title_template or config.get(
            "title_template", "{title} - Part {part_number}"
        )

        upload_parts(
            service,
            parts,
            base_title=args.title,
            description=args.description or "",
            tags=tags,
            category_id=category,
            privacy_status=privacy,
            title_template=title_template,
            thumbnail_path=thumbnail,
            playlist_id=playlist_id,
        )
    else:
        # Upload single file
        upload_video(
            service,
            input_path,
            title=args.title,
            description=args.description or "",
            tags=tags,
            category_id=category,
            privacy_status=privacy,
            thumbnail_path=thumbnail,
            playlist_id=playlist_id,
        )


def cmd_run(args, config):
    """Handle the 'run' subcommand - full pipeline."""
    # Step 1: Process
    if args.pitch is not None:
        config["pitch_shift"] = args.pitch
    if args.text is not None:
        config["watermark_text"] = args.text
    if args.remove_watermark is not None:
        config["remove_watermark"] = args.remove_watermark
    if args.blur_region is not None:
        config["blur_region"] = args.blur_region

    output_dir = config.get("output_dir", "output")
    base_name = os.path.splitext(os.path.basename(args.input))[0]
    processed_path = os.path.join(output_dir, f"{base_name}_processed.mp4")

    print("=" * 60)
    print("STEP 1/3: Processing video")
    print("=" * 60)
    process_video(args.input, processed_path, config, logo_path=args.logo)

    # Step 2: Split
    split_duration = args.split_duration or config.get("split_duration", 900)
    parts_dir = os.path.join(output_dir, f"{base_name}_parts")

    print("\n" + "=" * 60)
    print("STEP 2/3: Splitting video")
    print("=" * 60)
    parts = split_video(processed_path, parts_dir, split_duration)

    # Step 3: Upload
    print("\n" + "=" * 60)
    print("STEP 3/3: Uploading to YouTube")
    print("=" * 60)

    service = get_youtube_service()
    privacy = args.privacy or config.get("default_privacy", "private")
    category = args.category or config.get("category_id", "22")
    tags = args.tags or config.get("default_tags", [])
    title = args.title or base_name
    title_template = args.title_template or config.get(
        "title_template", "{title} - Part {part_number}"
    )

    thumbnail = args.thumbnail or config.get("thumbnail_path")

    # Resolve playlist
    playlist_id = None
    playlist_name = args.playlist or config.get("playlist_name")
    if playlist_name:
        from uploader.playlist import get_or_create_playlist
        playlist_id = get_or_create_playlist(service, playlist_name, privacy)

    upload_parts(
        service,
        parts,
        base_title=title,
        description=args.description or "",
        tags=tags,
        category_id=category,
        privacy_status=privacy,
        title_template=title_template,
        thumbnail_path=thumbnail,
        playlist_id=playlist_id,
    )

    print("\nPipeline complete!")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="ytupload",
        description="Automated video processing and YouTube upload pipeline",
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config file")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---- process ----
    proc = subparsers.add_parser("process", help="Process video (pitch + watermark)")
    proc.add_argument("input", help="Input video file path")
    proc.add_argument("-o", "--output", help="Output file path (default: <input>_processed.mp4)")
    proc.add_argument("--pitch", type=float, help="Pitch multiplier (e.g., 1.15 = 15%% higher)")
    proc.add_argument("--text", help="Text watermark to add")
    proc.add_argument("--logo", help="Path to PNG logo to overlay")
    proc.add_argument("--remove-watermark", metavar="X:Y:W:H", help="Remove watermark at x:y:width:height")
    proc.add_argument("--blur-region", metavar="X:Y:W:H", help="Blur region at x:y:width:height")
    proc.add_argument("--crf", type=int, help="Video quality CRF (0-51, lower=better)")
    proc.add_argument("--split", action="store_true", help="Split output into parts")
    proc.add_argument("--split-duration", type=int, help="Part duration in seconds (default: 900)")

    # ---- upload ----
    up = subparsers.add_parser("upload", help="Upload video(s) to YouTube")
    up.add_argument("input", help="Video file or directory of parts")
    up.add_argument("--title", required=True, help="Video title")
    up.add_argument("--description", default="", help="Video description")
    up.add_argument("--tags", nargs="+", help="Video tags")
    up.add_argument("--category", help="YouTube category ID")
    up.add_argument("--privacy", choices=["public", "private", "unlisted"], help="Privacy status")
    up.add_argument("--title-template", help='Title template (e.g., "{title} - Part {part_number}")')
    up.add_argument("--thumbnail", help="Path to thumbnail image (JPG/PNG)")
    up.add_argument("--playlist", help="YouTube playlist name (created if doesn't exist)")

    # ---- run (full pipeline) ----
    run = subparsers.add_parser("run", help="Full pipeline: process + split + upload")
    run.add_argument("input", help="Input video file path")
    run.add_argument("--title", help="YouTube title (default: filename)")
    run.add_argument("--description", default="", help="Video description")
    run.add_argument("--tags", nargs="+", help="Video tags")
    run.add_argument("--pitch", type=float, help="Pitch multiplier")
    run.add_argument("--text", help="Text watermark")
    run.add_argument("--logo", help="Path to PNG logo")
    run.add_argument("--remove-watermark", metavar="X:Y:W:H", help="Remove watermark region")
    run.add_argument("--blur-region", metavar="X:Y:W:H", help="Blur region")
    run.add_argument("--category", help="YouTube category ID")
    run.add_argument("--privacy", choices=["public", "private", "unlisted"], help="Privacy status")
    run.add_argument("--split-duration", type=int, help="Part duration in seconds")
    run.add_argument("--title-template", help='Title template')
    run.add_argument("--thumbnail", help="Path to thumbnail image (JPG/PNG)")
    run.add_argument("--playlist", help="YouTube playlist name (created if doesn't exist)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Change to script directory so relative paths work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    config = load_config(args.config)

    try:
        if args.command == "process":
            cmd_process(args, config)
        elif args.command == "upload":
            cmd_upload(args, config)
        elif args.command == "run":
            cmd_run(args, config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
