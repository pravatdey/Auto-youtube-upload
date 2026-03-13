"""Download files from Google Drive public/shared links."""

import os
import re

import requests

GDRIVE_URL_PATTERNS = [
    r"/file/d/([a-zA-Z0-9_-]+)",
    r"id=([a-zA-Z0-9_-]+)",
]


def extract_file_id(url: str) -> str:
    """Extract Google Drive file ID from various URL formats."""
    for pattern in GDRIVE_URL_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract file ID from URL: {url}")


def download_from_gdrive(url: str, output_dir: str = "downloads") -> str:
    """Download a file from Google Drive.

    Handles large-file confirmation cookie automatically.

    Args:
        url: Google Drive share/view URL
        output_dir: Directory to save the downloaded file

    Returns:
        Path to the downloaded file
    """
    file_id = extract_file_id(url)
    os.makedirs(output_dir, exist_ok=True)

    session = requests.Session()
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = session.get(download_url, stream=True)

    # Handle large file confirmation page
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            download_url = f"https://drive.google.com/uc?export=download&confirm={value}&id={file_id}"
            response = session.get(download_url, stream=True)
            break

    # Determine filename from Content-Disposition header or use file_id
    filename = f"{file_id}.mp4"
    cd = response.headers.get("content-disposition", "")
    if "filename=" in cd:
        matches = re.findall('filename="?([^"]+)"?', cd)
        if matches:
            filename = matches[0]

    output_path = os.path.join(output_dir, filename)

    print(f"Downloading from Google Drive: {file_id}")
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=32768):
            f.write(chunk)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Downloaded: {output_path} ({size_mb:.1f} MB)")
    return output_path
