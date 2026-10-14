from __future__ import annotations

import yt_dlp

from app.config import BACKEND_ROOT, MEDIA_ROOT

OUTPUT_DIR = MEDIA_ROOT / "original"   # where saved audio goes
BIN_DIR = BACKEND_ROOT / "bin"         # where ffmpeg + ffprobe live


class TikTokUnavailable(Exception):
    """yt-dlp couldn't get this TikTok: deleted, private, region-locked, or blocked."""


def _ydl_options() -> dict:
    """yt-dlp settings, built fresh each time so no two downloads share one dict."""
    return {
        # grab the best audio-only stream (fall back to best overall)
        "format": "bestaudio/best",
        "outtmpl": str(OUTPUT_DIR / "%(id)s.%(ext)s"),
        "ffmpeg_location": str(BIN_DIR),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }


def fetch_info(url: str) -> dict:
    """Look up a TikTok's metadata, including its video id, WITHOUT downloading.

    This lets the caller check the database for the video id first and skip
    the download entirely if the clip is already saved.
    """
    try:
        with yt_dlp.YoutubeDL(_ydl_options()) as ydl:
            return ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        raise TikTokUnavailable(str(e)) from e


def download_audio(info: dict) -> dict:
    """Download the audio described by `info` (the result of fetch_info).

    Reuses the info yt-dlp already fetched, so TikTok isn't looked up twice.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)   # create the folder if it's missing

    try:
        with yt_dlp.YoutubeDL(_ydl_options()) as ydl:
            info = ydl.process_ie_result(info, download=True)
    except yt_dlp.utils.DownloadError as e:
        raise TikTokUnavailable(str(e)) from e

    saved_file_path = OUTPUT_DIR / f"{info['id']}.{info['ext']}"

    metadata = {
        "title": info.get("title", "Unknown Title"),
        "uploader": info.get("uploader", "Unknown Uploader"),
        "duration": info.get("duration", 0),
        "thumbnail": info.get("thumbnail", ""),
    }

    # Return the path RELATIVE to MEDIA_ROOT ("original/<id>.mp3"), not the
    # full path on this machine, so it stays valid if the backend moves.
    # as_posix() uses forward slashes on every OS.
    return {
        "video_id": info["id"],
        "file_path": saved_file_path.relative_to(MEDIA_ROOT).as_posix(),
        "metadata": metadata,
    }


def extract_audio(url: str) -> dict:
    """Look up and download in one step (handy for testing from the terminal)."""
    return download_audio(fetch_info(url))


# A tiny CLI so you can test from the terminal.
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.services.audio_extractor <tiktok_url>")
        raise SystemExit(1)

    result = extract_audio(sys.argv[1])
    print(result)
