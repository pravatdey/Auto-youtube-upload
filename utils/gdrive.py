"""Google Drive upload/download utilities."""

import os
import re

import gdown


GDRIVE_URL_PATTERNS = [
    r"/file/d/([a-zA-Z0-9_-]+)",
    r"id=([a-zA-Z0-9_-]+)",
]

# Scopes needed for Drive upload + sharing
DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]

DRIVE_TOKEN_FILE = "config/gdrive_token.json"
CLIENT_SECRETS_FILE = "config/client_secrets.json"


def extract_file_id(url: str) -> str:
    """Extract Google Drive file ID from various URL formats."""
    for pattern in GDRIVE_URL_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract file ID from URL: {url}")


def download_from_gdrive(url: str, output_dir: str = "downloads") -> str:
    """Download a file from Google Drive."""
    file_id = extract_file_id(url)
    os.makedirs(output_dir, exist_ok=True)

    gdrive_url = f"https://drive.google.com/uc?id={file_id}"

    print(f"Downloading from Google Drive: {file_id}")
    output_path = gdown.download(gdrive_url, output=output_dir + "/", fuzzy=True)

    if output_path is None:
        raise RuntimeError(
            f"Failed to download from Google Drive. "
            f"Make sure the file is shared as 'Anyone with the link can view'.\n"
            f"File ID: {file_id}"
        )

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Downloaded: {output_path} ({size_mb:.1f} MB)")
    return output_path


def get_drive_service():
    """Authenticate and return Google Drive API service."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None

    if os.path.isfile(DRIVE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(DRIVE_TOKEN_FILE, DRIVE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, DRIVE_SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(DRIVE_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print("Google Drive authenticated.")

    return build("drive", "v3", credentials=creds)


def upload_to_drive(file_path: str, folder_name: str = "UPSC Notes",
                    share_public: bool = True) -> dict:
    """Upload a file to Google Drive and optionally make it public.

    Args:
        file_path: Local file to upload
        folder_name: Drive folder name (created if doesn't exist)
        share_public: Make the file viewable by anyone with the link

    Returns:
        dict with 'file_id', 'web_view_link', 'web_content_link'
    """
    from googleapiclient.http import MediaFileUpload

    service = get_drive_service()
    file_name = os.path.basename(file_path)

    # Find or create folder
    folder_id = _get_or_create_folder(service, folder_name)

    # Upload file
    file_metadata = {
        "name": file_name,
        "parents": [folder_id],
    }

    # Detect mime type
    ext = os.path.splitext(file_path)[1].lower()
    mime_types = {
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".json": "application/json",
        ".mp4": "video/mp4",
        ".png": "image/png",
        ".jpg": "image/jpeg",
    }
    mime_type = mime_types.get(ext, "application/octet-stream")

    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

    print(f"Uploading {file_name} to Google Drive/{folder_name}...")
    file = service.files().create(
        body=file_metadata, media_body=media, fields="id,webViewLink,webContentLink"
    ).execute()

    file_id = file.get("id")
    result = {
        "file_id": file_id,
        "web_view_link": file.get("webViewLink", ""),
        "web_content_link": file.get("webContentLink", ""),
    }

    # Make public
    if share_public:
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()
        result["share_link"] = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        print(f"Shared publicly: {result['share_link']}")

    print(f"Upload complete! File ID: {file_id}")
    return result


def _get_or_create_folder(service, folder_name: str) -> str:
    """Find or create a folder in Google Drive root."""
    # Search for existing folder
    query = (
        f"name = '{folder_name}' and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"trashed = false"
    )
    results = service.files().list(q=query, spaces="drive", fields="files(id)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # Create folder
    folder_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = service.files().create(body=folder_metadata, fields="id").execute()
    print(f"Created folder: {folder_name}")
    return folder["id"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Upload file to Google Drive and share")
    parser.add_argument("file", help="File to upload")
    parser.add_argument("--folder", default="UPSC Notes", help="Drive folder name")
    parser.add_argument("--no-share", action="store_true", help="Don't make public")

    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    result = upload_to_drive(args.file, args.folder, share_public=not args.no_share)

    print(f"\nShare this link with your viewers:")
    print(f"  {result.get('share_link', result.get('web_view_link', ''))}")

