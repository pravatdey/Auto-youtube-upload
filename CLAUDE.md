# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this project is

Automated pipeline to **process videos and upload them to YouTube** for an
education channel (UPSC / competitive-exam prep). It downloads source videos
from Google Drive, transforms them (pitch shift, watermark/branding, logo
overlays to cover third-party branding), splits long videos into parts, and
uploads each part to YouTube — optionally into a playlist with a thumbnail.

There are two layers in this repo:

1. **The core pipeline** (`main.py` + `pipeline/` + `uploader/` + `utils/`) —
   the reusable, config-driven engine.
2. **Many standalone "content" scripts** at the repo root (e.g.
   `create_news_video.py`, `create_opsc_video.py`, `cjp_*.py`,
   `generate_gemini_audio.py`, `upsc_2026/`) — one-off / per-series generators
   that build narrated videos from scratch (TTS audio + images + FFmpeg). These
   are largely independent of the core pipeline.

## Core pipeline architecture

```
main.py            CLI entry point: `process`, `upload`, `run` subcommands
ci_run.py          Headless runner used by GitHub Actions; reads jobs.yaml
config.yaml        All tunable settings (pitch, watermark, tags, templates, paths)
jobs.yaml          Queue of upload jobs; pushing changes here triggers CI

pipeline/
  processor.py       Orchestrates the FFmpeg processing pass
  ffmpeg_filters.py  Builds audio (pitch) + video (watermark/logo/blur) filters
  splitter.py        Splits processed video into fixed-duration parts
  notes.py           (content helper)
  rebrand.py         (content helper)

uploader/
  auth.py          OAuth2 -> authenticated YouTube service
  youtube.py       upload_video / upload_parts (resumable upload, thumbnails)
  playlist.py      get_or_create_playlist (cached in config/playlists.json)

utils/
  ffprobe.py       Probe video/audio info (sample rate, dimensions, duration)
  gdrive.py        Download source video from a Google Drive share URL
```

### Data flow (full pipeline)

`gdrive URL` → download → `process_video` (pitch + branding) → `split_video`
(parts) → `upload_parts` → YouTube (+ playlist + thumbnail).

## How to run

```bash
pip install -r requirements.txt   # needs FFmpeg + ffprobe on PATH

# Process only (pitch shift + watermark)
python main.py process <video.mp4> --split

# Upload only (single file or a directory of parts)
python main.py upload <video_or_dir> --title "My Title"

# Full pipeline: process + split + upload
python main.py run <video.mp4> --title "My Title"
```

Most behaviour is driven by `config.yaml`; CLI flags override it.

## CI / automation

`.github/workflows/auto-upload.yml` runs on push to `jobs.yaml` (or manual
dispatch). It installs FFmpeg, restores credentials from repo **secrets**
(`CLIENT_SECRETS_JSON`, `YOUTUBE_TOKEN_JSON`), runs `ci_run.py`, and commits the
updated `config/playlists.json` cache. To queue an upload, add a job to
`jobs.yaml` and push.

## Secrets — do not commit

These are gitignored and must **never** be committed:

- `config/client_secrets.json` — Google OAuth client secret
- `config/youtube_token.json` — YouTube OAuth token
- `.env` — API keys (e.g. Gemini, GitHub)

`*.pickle` and `token.pickle` are also ignored. In CI, credentials come from
GitHub Actions secrets, not the repo.

## Conventions / notes

- **Windows-first environment.** Default paths in `config.yaml` point at
  `C:/Users/.../Downloads`, output to `output/`, and FFmpeg temp to `D:/temp`
  (the C: drive is space-constrained). Adjust paths for other machines.
- All heavy media work shells out to **FFmpeg/ffprobe** via `subprocess`; make
  sure both are installed and on `PATH`.
- `output/`, `downloads/`, and large generated media are gitignored.
- The standalone content scripts at the repo root are experimental and often
  series-specific; prefer reading the one you need rather than assuming shared
  structure with the core pipeline.
