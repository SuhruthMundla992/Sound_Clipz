"""
extractor.py — TikTok link -> audio file.

This is the heart of the backend. It hands a TikTok URL to yt-dlp, pulls the
best available audio, and saves it as an .m4a (AAC) file — preferring to COPY
the original audio stream rather than re-encode it, so we don't lose quality
a second time (see tech_stack_plan.md, section 2).

Requires ffmpeg to be installed (yt-dlp uses it to extract/remux the audio).

Usage as a script (for quick testing):
    python -m app.services.extractor "https://vm.tiktok.com/XXXXXXX/"
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import yt_dlp


# Where extracted originals land by default. Resolved relative to backend/.
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "media" / "original"


@dataclass
class ExtractedClip:
    """The result of one extraction — what we hand back to the rest of the app."""

    source_url: str          # the TikTok link we were given
    audio_path: Path         # where the .m4a file was saved
    title: str               # video title / description
    uploader: str            # the TikTok creator's handle
    duration: float | None   # length in seconds
    thumbnail_url: str | None  # cover image URL (we can download it later)


def extract_audio(url: str, output_dir: Path = DEFAULT_OUTPUT_DIR) -> ExtractedClip:
    """
    Download the audio from a TikTok URL and save it as .m4a.

    Returns an ExtractedClip with the file path + metadata.
    Raises yt_dlp.utils.DownloadError if the link can't be fetched.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # yt-dlp options. The two that matter most:
    #   format: "bestaudio/best" -> grab the highest-quality audio stream
    #           available (falls back to best overall if there's no audio-only).
    #   FFmpegExtractAudio -> pull the audio out into an .m4a container. yt-dlp
    #           copies the AAC stream when it can, so this stays lossless for
    #           TikTok's already-AAC audio.
    ydl_opts = {
        "format": "bestaudio/best",
        # %(id)s = TikTok's own unique id -> stable, collision-free filenames.
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "0",  # 0 = best; only matters if re-encoding
            }
        ],
        "quiet": True,
        "no_warnings": True,
        # Keep console noise down; flip to False while debugging a bad link.
        "noprogress": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # download=True actually fetches + runs the postprocessor.
        info = ydl.extract_info(url, download=True)

    # After extraction the file is <id>.m4a in output_dir.
    audio_path = output_dir / f"{info['id']}.m4a"

    return ExtractedClip(
        source_url=url,
        audio_path=audio_path,
        title=info.get("title") or info.get("description") or "Untitled",
        uploader=info.get("uploader") or info.get("uploader_id") or "unknown",
        duration=info.get("duration"),
        thumbnail_url=info.get("thumbnail"),
    )


def _main() -> None:
    """Tiny CLI so you can test extraction from the terminal."""
    if len(sys.argv) != 2:
        print("Usage: python -m app.services.extractor <tiktok_url>")
        raise SystemExit(1)

    clip = extract_audio(sys.argv[1])
    print("Extracted!")
    print(f"  title:     {clip.title}")
    print(f"  uploader:  {clip.uploader}")
    print(f"  duration:  {clip.duration}s")
    print(f"  saved to:  {clip.audio_path}")


if __name__ == "__main__":
    _main()
