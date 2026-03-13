"""CI runner script for GitHub Actions - processes jobs from jobs.yaml."""

import os
import sys

import yaml

from pipeline.processor import process_video
from pipeline.splitter import split_video
from uploader.auth import get_youtube_service
from uploader.playlist import get_or_create_playlist
from uploader.youtube import upload_parts
from utils.gdrive import download_from_gdrive


def run_jobs():
    """Read jobs.yaml and run the full pipeline for each job."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Load configs
    with open("jobs.yaml", "r") as f:
        jobs_data = yaml.safe_load(f) or {}
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f) or {}

    jobs = jobs_data.get("jobs") or []
    if not jobs:
        print("No jobs found in jobs.yaml")
        return

    service = get_youtube_service()

    for i, job in enumerate(jobs, 1):
        print(f"\n{'='*60}")
        print(f"JOB {i}/{len(jobs)}: {job['title']}")
        print(f"{'='*60}")

        # Step 1: Download from Google Drive
        print("\n--- Downloading from Google Drive ---")
        video_path = download_from_gdrive(job["gdrive_url"], output_dir="downloads")

        # Validate download
        file_size = os.path.getsize(video_path) / (1024 * 1024)
        if file_size < 1:
            raise RuntimeError(
                f"Downloaded file is too small ({file_size:.1f} MB). "
                f"The Google Drive file may not be shared publicly."
            )

        # Step 2: Process video
        output_dir = config.get("output_dir", "output")
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        processed_path = os.path.join(output_dir, f"{base_name}_processed.mp4")

        job_config = {**config}
        if "pitch" in job:
            job_config["pitch_shift"] = job["pitch"]

        print("\n--- Processing video ---")
        process_video(video_path, processed_path, job_config)

        # Step 3: Split
        split_duration = job.get("split_duration", config.get("split_duration", 900))
        parts_dir = os.path.join(output_dir, f"{base_name}_parts")

        print("\n--- Splitting video ---")
        parts = split_video(processed_path, parts_dir, split_duration)

        # Step 4: Resolve playlist
        playlist_id = None
        playlist_name = job.get("playlist")
        privacy = job.get("privacy", config.get("default_privacy", "private"))
        if playlist_name:
            playlist_id = get_or_create_playlist(service, playlist_name, privacy)

        # Step 5: Upload
        tags = job.get("tags", config.get("default_tags", []))
        title_template = config.get("title_template", "{title} - Part {part_number}")
        thumbnail = config.get("thumbnail_path")

        print("\n--- Uploading to YouTube ---")
        upload_parts(
            service,
            parts,
            base_title=job["title"],
            description=job.get("description", ""),
            tags=tags,
            category_id=config.get("category_id", "22"),
            privacy_status=privacy,
            title_template=title_template,
            thumbnail_path=thumbnail,
            playlist_id=playlist_id,
        )

    print(f"\nAll {len(jobs)} jobs complete!")


if __name__ == "__main__":
    try:
        run_jobs()
    except Exception as e:
        print(f"CI run failed: {e}", file=sys.stderr)
        sys.exit(1)
