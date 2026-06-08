"""Upload a previously created news video to YouTube.

Usage:
    python upload_news_video.py
    python upload_news_video.py --metadata "D:/temp/India_South_Korea_Trade_Deal_metadata.json"
    python upload_news_video.py --playlist "Current Affairs 2026"
"""

import argparse
import json
import os
import sys

import yaml

from uploader.auth import get_youtube_service
from uploader.youtube import upload_video
from uploader.playlist import get_or_create_playlist


def main():
    parser = argparse.ArgumentParser(description="Upload news video to YouTube")
    parser.add_argument("--metadata", default="D:/temp/India_South_Korea_Trade_Deal_metadata.json",
                        help="Path to metadata JSON from create_news_video.py")
    parser.add_argument("--playlist", default="Current Affairs 2026",
                        help="YouTube playlist name")
    parser.add_argument("--privacy", default=None, help="Override privacy (public/private/unlisted)")
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Load metadata
    if not os.path.isfile(args.metadata):
        print(f"Metadata file not found: {args.metadata}")
        print("Run create_news_video.py first to generate the video.")
        sys.exit(1)

    with open(args.metadata, "r", encoding="utf-8") as f:
        meta = json.load(f)

    video_path = meta["video_path"]
    if not os.path.isfile(video_path):
        print(f"Video file not found: {video_path}")
        sys.exit(1)

    print("=" * 60)
    print("  UPLOADING TO YOUTUBE")
    print("=" * 60)
    print(f"  Video: {video_path}")
    print(f"  Title: {meta['title']}")
    print(f"  Privacy: {args.privacy or meta.get('privacy', 'public')}")
    print(f"  Playlist: {args.playlist}")
    print("=" * 60)

    service = get_youtube_service()
    privacy = args.privacy or meta.get("privacy", "public")

    # Get or create playlist
    playlist_id = get_or_create_playlist(service, args.playlist, privacy)

    # Upload
    video_id = upload_video(
        service,
        video_path,
        title=meta["title"],
        description=meta.get("description", ""),
        tags=meta.get("tags", []),
        category_id=meta.get("category_id", "27"),
        privacy_status=privacy,
        thumbnail_path=meta.get("thumbnail_path"),
        playlist_id=playlist_id,
    )

    print(f"\n{'=' * 60}")
    print(f"  UPLOADED SUCCESSFULLY!")
    print(f"  Video ID: {video_id}")
    print(f"  URL: https://youtube.com/watch?v={video_id}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
