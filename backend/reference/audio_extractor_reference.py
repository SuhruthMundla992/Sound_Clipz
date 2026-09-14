"""
audio_extractor.py — take a clean TikTok URL, extract the audio, save it.

Responsibility: the actual yt-dlp + ffmpeg work. Given a URL (already cleaned by
share_extract.py), download the media, pull out the audio as .m4a, and save it to
disk — returning the file path plus metadata.

This file assumes it's handed a good URL; cleaning/validation is share_extract's job.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yt_dlp

# --- Locations, anchored to the backend/ root so this works from anywhere ---
# __file__ = backend/app/services/audio_extractor.py
# parents[2] = backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]
BIN_DIR = BACKEND_ROOT / "bin"                       # our ffmpeg + ffprobe live here
DEFAULT_OUTPUT_DIR = BACKEND_ROOT / "media" / "original"


@dataclass
class ExtractedClip:
    """What we hand back after a successful extraction."""

    source_url: str
    audio_path: Path
    title: str
    uploader: str
    duration: float | None
    thumbnail_url: str | None


def extract_audio(url: str, output_dir: Path = DEFAULT_OUTPUT_DIR) -> ExtractedClip:
    """
    Download audio from a (clean) TikTok URL and save it as .m4a.

    Returns an ExtractedClip with the saved file path + metadata.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        # Grab the best audio stream; fall back to best overall if there's no
        # audio-only format (TikTok serves one mp4, so this pulls audio from it).
        "format": "bestaudio/best",
        # Name the file by TikTok's unique id -> no collisions.
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        # Use OUR ffmpeg/ffprobe in backend/bin, not a system install.
        "ffmpeg_location": str(BIN_DIR),
        # After download, extract the audio into an .m4a container. yt-dlp copies
        # the AAC stream when it can, so we don't re-encode (keeps quality).
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "0",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    audio_path = output_dir / f"{info['id']}.m4a"

    return ExtractedClip(
        source_url=url,
        audio_path=audio_path,
        title=info.get("title") or info.get("description") or "Untitled",
        uploader=info.get("uploader") or info.get("uploader_id") or "unknown",
        duration=info.get("duration"),
        thumbnail_url=info.get("thumbnail"),
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.services.audio_extractor <tiktok_url>")
        raise SystemExit(1)

    clip = extract_audio(sys.argv[1])
    print("Extracted!")
    print(f"  title:    {clip.title}")
    print(f"  uploader: {clip.uploader}")
    print(f"  duration: {clip.duration}s")
    print(f"  saved to: {clip.audio_path}")
