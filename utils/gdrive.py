"""Download files from Google Drive public/shared links."""

import os
import re

import gdown


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

    Uses gdown to handle large files, confirmation pages, and cookies.

    Args:
        url: Google Drive share/view URL
        output_dir: Directory to save the downloaded file

    Returns:
        Path to the downloaded file
    """
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
