import json
import subprocess


def get_video_info(video_path: str) -> dict:
    """Get video metadata using ffprobe.

    Returns dict with keys: duration, width, height, sample_rate, video_codec, audio_codec
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            video_path,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    data = json.loads(result.stdout)
    info = {
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "sample_rate": 44100,
        "video_codec": "",
        "audio_codec": "",
    }

    # Get duration from format (more reliable)
    if "format" in data and "duration" in data["format"]:
        info["duration"] = float(data["format"]["duration"])

    for stream in data.get("streams", []):
        if stream["codec_type"] == "video" and not info["video_codec"]:
            info["width"] = int(stream.get("width", 0))
            info["height"] = int(stream.get("height", 0))
            info["video_codec"] = stream.get("codec_name", "")
            # Fallback duration from video stream
            if info["duration"] == 0.0 and "duration" in stream:
                info["duration"] = float(stream["duration"])

        elif stream["codec_type"] == "audio" and not info["audio_codec"]:
            info["sample_rate"] = int(stream.get("sample_rate", 44100))
            info["audio_codec"] = stream.get("codec_name", "")

    return info
