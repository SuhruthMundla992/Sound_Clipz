"""
audio_extractor.py — take a clean TikTok URL, extract the audio, save it.

YOU are writing this one. The gameplan is laid out as TODO steps below.
Fill in the code under each step. Run it often — don't write all of it at once.

A reference version lives in reference/audio_extractor_reference.py — only
peek if you're truly stuck.
"""

from __future__ import annotations
import yt_dlp
import pathlib
import os


# --- Locations ---
# TODO Step 1: define where files go.
#   - the folder for saved audio (media/original)
#   - the folder where ffmpeg + ffprobe live (backend/bin)
#   Tip: anchor them to the backend root so this works from any directory.


def extract_audio(url: str):
    """
    Download audio from a (clean) TikTok URL and save it as .m4a.
    Return the saved file path + metadata (you decide the shape).
    """
    # TODO Step 1 (cont.): make sure the output folder exists.

    # TODO Step 2: build the yt-dlp options dict.
    #   - format: best audio
    #   - outtmpl: name the file (hint: by the video's id)
    #   - ffmpeg_location: point at your backend/bin
    #   - postprocessors: FFmpegExtractAudio -> m4a
    #   - (optional) quiet / no_warnings / noprogress

    # TODO Step 3: run the download.
    #   - open a YoutubeDL context with your options
    #   - call extract_info(url, download=True) and keep the returned info dict
    #   - TIP for your FIRST run: just `print(info)` here and stop, to SEE what
    #     yt-dlp gives you. Then continue with steps 4-6.

    # TODO Step 4: figure out the saved file path (from the id + .m4a).

    # TODO Step 5: pull the metadata you want out of info
    #   (title, uploader, duration, thumbnail) — use .get() with fallbacks.

    # TODO Step 6: return it (dict? dataclass? your call).
    raise NotImplementedError  # remove this once you return something


# A tiny CLI so you can test from the terminal.
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.services.audio_extractor <tiktok_url>")
        raise SystemExit(1)

    result = extract_audio(sys.argv[1])
    print(result)
