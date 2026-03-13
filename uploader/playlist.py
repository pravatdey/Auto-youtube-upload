"""YouTube playlist management - create, find, and add videos to playlists."""

import json
import os
from pathlib import Path

from googleapiclient.errors import HttpError

PLAYLIST_CACHE_FILE = "config/playlists.json"


def _load_playlist_cache() -> dict[str, str]:
    """Load playlist name -> ID mapping from local cache."""
    if not os.path.isfile(PLAYLIST_CACHE_FILE):
        return {}
    with open(PLAYLIST_CACHE_FILE, "r") as f:
        return json.load(f)


def _save_playlist_cache(cache: dict[str, str]) -> None:
    """Save playlist name -> ID mapping to local cache."""
    Path(PLAYLIST_CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(PLAYLIST_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_or_create_playlist(
    service, playlist_name: str, privacy_status: str = "private"
) -> str:
    """Find existing playlist by name or create a new one. Returns playlist ID."""
    # Step 1: Check local cache
    cache = _load_playlist_cache()
    if playlist_name in cache:
        print(f"  Playlist '{playlist_name}' found in cache: {cache[playlist_name]}")
        return cache[playlist_name]

    # Step 2: Search YouTube for existing playlist
    print(f"  Searching YouTube for playlist '{playlist_name}'...")
    next_page = None
    while True:
        response = service.playlists().list(
            part="snippet", mine=True, maxResults=50, pageToken=next_page
        ).execute()
        for item in response.get("items", []):
            if item["snippet"]["title"] == playlist_name:
                playlist_id = item["id"]
                cache[playlist_name] = playlist_id
                _save_playlist_cache(cache)
                print(f"  Found existing playlist: {playlist_id}")
                return playlist_id
        next_page = response.get("nextPageToken")
        if not next_page:
            break

    # Step 3: Create new playlist
    print(f"  Creating new playlist '{playlist_name}'...")
    body = {
        "snippet": {
            "title": playlist_name,
            "description": f"Auto-created playlist: {playlist_name}",
        },
        "status": {"privacyStatus": privacy_status},
    }
    response = service.playlists().insert(part="snippet,status", body=body).execute()
    playlist_id = response["id"]
    cache[playlist_name] = playlist_id
    _save_playlist_cache(cache)
    print(f"  Created playlist: {playlist_id}")
    return playlist_id


def add_video_to_playlist(service, playlist_id: str, video_id: str) -> bool:
    """Add a video to a YouTube playlist. Returns True on success."""
    try:
        service.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                }
            },
        ).execute()
        print(f"  Added video {video_id} to playlist {playlist_id}")
        return True
    except HttpError as e:
        print(f"  Failed to add to playlist: {e.resp.status} - {e.content.decode()}")
        return False
