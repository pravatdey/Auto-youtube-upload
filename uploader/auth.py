"""YouTube OAuth2 authentication with JSON token caching.

Uses the same credential format as Ai-current-affairs-model project.
"""

import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

CLIENT_SECRETS_FILE = "config/client_secrets.json"
TOKEN_FILE = "config/youtube_token.json"


def _load_credentials() -> Credentials | None:
    """Load credentials from JSON token file."""
    if not os.path.isfile(TOKEN_FILE):
        return None

    with open(TOKEN_FILE, "r", encoding="utf-8-sig") as f:
        token_data = json.load(f)

    required = ["token", "refresh_token", "token_uri", "client_id", "client_secret"]
    if any(not token_data.get(k) for k in required):
        return None

    return Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data.get("scopes"),
    )


def _save_credentials(credentials: Credentials) -> None:
    """Save credentials to JSON token file."""
    Path(TOKEN_FILE).parent.mkdir(parents=True, exist_ok=True)

    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)


def get_youtube_service():
    """Get an authenticated YouTube Data API v3 service.

    First run opens a browser for OAuth consent.
    Subsequent runs use cached token with auto-refresh.
    """
    if not os.path.isfile(CLIENT_SECRETS_FILE):
        raise FileNotFoundError(
            f"'{CLIENT_SECRETS_FILE}' not found.\n"
            "Steps to create it:\n"
            "1. Go to https://console.cloud.google.com\n"
            "2. Create a project and enable 'YouTube Data API v3'\n"
            "3. Create OAuth 2.0 credentials (Desktop app type)\n"
            "4. Download the JSON and save it as 'config/client_secrets.json'"
        )

    credentials = _load_credentials()

    if credentials and credentials.valid:
        print("Using existing YouTube credentials.")
        return build("youtube", "v3", credentials=credentials)

    if credentials and credentials.expired and credentials.refresh_token:
        print("Refreshing YouTube credentials...")
        try:
            credentials.refresh(Request())
            _save_credentials(credentials)
            print("Credentials refreshed.")
            return build("youtube", "v3", credentials=credentials)
        except Exception as e:
            print(f"Token refresh failed: {e}, starting new auth flow...")

    # New authentication - not possible in CI
    if os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"):
        raise RuntimeError(
            "YouTube token is expired and cannot be refreshed in CI.\n"
            "Run 'python -m uploader.auth --auth' locally and update the "
            "YOUTUBE_TOKEN_JSON GitHub secret with the new token."
        )

    print("Opening browser for YouTube OAuth authentication...")
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES
    )
    credentials = flow.run_local_server(port=0)
    _save_credentials(credentials)
    print("Credentials saved.")

    return build("youtube", "v3", credentials=credentials)


def get_channel_info(service) -> dict:
    """Get authenticated channel info for verification."""
    try:
        response = service.channels().list(
            part="snippet,statistics",
            mine=True,
        ).execute()

        if response.get("items"):
            ch = response["items"][0]
            return {
                "id": ch["id"],
                "title": ch["snippet"]["title"],
                "subscribers": ch["statistics"].get("subscriberCount", 0),
                "videos": ch["statistics"].get("videoCount", 0),
            }
    except Exception as e:
        print(f"Failed to get channel info: {e}")

    return {}


# CLI for testing auth
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Auth Test")
    parser.add_argument("--auth", action="store_true", help="Test authentication")
    parser.add_argument("--info", action="store_true", help="Get channel info")
    args = parser.parse_args()

    # Change to project root
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    if args.auth or args.info:
        service = get_youtube_service()
        info = get_channel_info(service)
        if info:
            print(f"\nChannel: {info['title']}")
            print(f"ID: {info['id']}")
            print(f"Subscribers: {info['subscribers']}")
            print(f"Videos: {info['videos']}")
            print("Authentication successful!")
        else:
            print("Authenticated but couldn't get channel info.")
    else:
        parser.print_help()
