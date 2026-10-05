from __future__ import annotations
import yt_dlp
import pathlib
import os


# Anchor everything to backend/ so it works no matter where we run from.
BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_DIR = BACKEND_ROOT / "media" / "original"   # where saved audio goes
BIN_DIR = BACKEND_ROOT / "bin"                       # where ffmpeg + ffprobe live


def extract_audio(url: str):





    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    #create the output if alrady not created


    options = {
        # grab the best audio-only stream (fall back to best overall)
        "format": "bestaudio/best",
        "outtmpl": str(OUTPUT_DIR / "%(id)s.%(ext)s"),
        "ffmpeg_location": str(BIN_DIR),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }


    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)

    vid_id = info.get("id")
    saved_file_path = OUTPUT_DIR / f"{vid_id}.{info.get('ext')}"


    metadata = {
        "title": info.get("title", "Unknown Title"),
        "uploader": info.get("uploader", "Unknown Uploader"),
        "duration": info.get("duration", 0),
        "thumbnail": info.get("thumbnail", ""),
    }


    return {
        "file_path": str(saved_file_path),
        "metadata": metadata,
    }



# A tiny CLI so you can test from the terminal.
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.services.audio_extractor <tiktok_url>")
        raise SystemExit(1)

    result = extract_audio(sys.argv[1])
    print(result)
