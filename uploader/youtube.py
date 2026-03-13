"""YouTube video upload with resumable upload and exponential backoff retry."""

import http.client
import os
import sys
import time
from dataclasses import dataclass

import httplib2
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

MAX_RETRIES = 10
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (
    httplib2.HttpLib2Error,
    IOError,
    http.client.NotConnected,
    http.client.IncompleteRead,
    http.client.ImproperConnectionState,
    http.client.CannotSendRequest,
    http.client.CannotSendHeader,
    http.client.ResponseNotReady,
    http.client.BadStatusLine,
)
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB (matching reference project)


@dataclass
class UploadResult:
    """Result of video upload."""
    success: bool
    video_id: str
    video_url: str
    title: str
    error: str | None = None


def set_thumbnail(service, video_id: str, thumbnail_path: str) -> bool:
    """Set a custom thumbnail for an uploaded video."""
    if not thumbnail_path or not os.path.isfile(thumbnail_path):
        return False
    try:
        media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
        service.thumbnails().set(videoId=video_id, media_body=media).execute()
        print(f"  Thumbnail set: {os.path.basename(thumbnail_path)}")
        return True
    except HttpError as e:
        print(f"  Thumbnail failed: {e.resp.status} - {e.content.decode()}")
        return False


def upload_video(
    service,
    video_path: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    category_id: str = "22",
    privacy_status: str = "private",
    thumbnail_path: str | None = None,
    playlist_id: str | None = None,
) -> UploadResult:
    """Upload a single video to YouTube.

    Returns:
        UploadResult with video_id and url on success
    """
    if not os.path.isfile(video_path):
        return UploadResult(
            success=False, video_id="", video_url="", title=title,
            error=f"Video not found: {video_path}",
        )

    try:
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags or [],
                "categoryId": category_id,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
                "embeddable": True,
                "publicStatsViewable": True,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/*",
            chunksize=CHUNK_SIZE,
            resumable=True,
        )

        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        file_size = os.path.getsize(video_path) / (1024 * 1024)
        print(f"\nUploading: {os.path.basename(video_path)} ({file_size:.1f} MB)")
        print(f"  Title: {title}")
        print(f"  Privacy: {privacy_status}")

        response = _resumable_upload(request)

        if response and "id" in response:
            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"  Uploaded! Video ID: {video_id}")
            print(f"  URL: {video_url}")
            if thumbnail_path:
                set_thumbnail(service, video_id, thumbnail_path)
            if playlist_id:
                from uploader.playlist import add_video_to_playlist
                add_video_to_playlist(service, playlist_id, video_id)
            return UploadResult(
                success=True, video_id=video_id, video_url=video_url, title=title,
            )

        return UploadResult(
            success=False, video_id="", video_url="", title=title,
            error="Upload failed - no response",
        )

    except HttpError as e:
        error_msg = f"HTTP error {e.resp.status}: {e.content.decode()}"
        print(f"  Upload failed: {error_msg}")
        return UploadResult(
            success=False, video_id="", video_url="", title=title, error=error_msg,
        )

    except Exception as e:
        print(f"  Upload failed: {e}")
        return UploadResult(
            success=False, video_id="", video_url="", title=title, error=str(e),
        )


def _resumable_upload(request) -> dict | None:
    """Execute resumable upload with exponential backoff."""
    response = None
    error = None
    retry = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                sys.stdout.write(f"\r  Upload progress: {progress}%  ")
                sys.stdout.flush()
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"Retriable HTTP error {e.resp.status}: {e.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"Retriable error: {e}"

        if error:
            retry += 1
            if retry > MAX_RETRIES:
                print(f"\n  Max retries exceeded. Last error: {error}")
                return None
            sleep_seconds = 2 ** retry
            print(f"\n  Error, retrying in {sleep_seconds}s ({retry}/{MAX_RETRIES}): {error}")
            time.sleep(sleep_seconds)
            error = None

    print()  # newline after progress
    return response


def upload_parts(
    service,
    parts: list[str],
    base_title: str,
    description: str = "",
    tags: list[str] | None = None,
    category_id: str = "22",
    privacy_status: str = "private",
    title_template: str = "{title} - Part {part_number}",
    thumbnail_path: str | None = None,
    playlist_id: str | None = None,
) -> list[UploadResult]:
    """Upload multiple video parts to YouTube.

    Returns:
        List of UploadResult objects
    """
    total = len(parts)
    results = []

    print(f"\n{'='*50}")
    print(f"Uploading {total} parts to YouTube")
    print(f"{'='*50}")

    for i, part_path in enumerate(parts, 1):
        title = title_template.format(
            title=base_title,
            part_number=i,
            total_parts=total,
        )

        part_desc = f"{description}\n\nPart {i} of {total}".strip()

        result = upload_video(
            service,
            part_path,
            title=title,
            description=part_desc,
            tags=tags,
            category_id=category_id,
            privacy_status=privacy_status,
            thumbnail_path=thumbnail_path,
            playlist_id=playlist_id,
        )
        results.append(result)

        status_text = "Done" if result.success else f"FAILED: {result.error}"
        print(f"  [{i}/{total}] {status_text}")

    # Summary
    successful = sum(1 for r in results if r.success)
    print(f"\n{'='*50}")
    print(f"Upload complete: {successful}/{total} successful")
    for i, r in enumerate(results, 1):
        url = r.video_url if r.success else f"FAILED: {r.error}"
        print(f"  Part {i}: {url}")
    print(f"{'='*50}")

    return results
