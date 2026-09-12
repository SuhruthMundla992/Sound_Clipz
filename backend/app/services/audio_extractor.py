"""
audio_extractor.py — take a clean TikTok URL, extract the audio, save it.

Responsibility: the actual yt-dlp + ffmpeg work. Given a URL (already cleaned by
share_extract.py), download the media, pull out the audio as .m4a, and save it to
disk — returning the file path plus metadata.

This file assumes it's handed a good URL; cleaning/validation is share_extract's job.
"""

from __future__ import annotations


def extract_audio(url: str):
    """
    Download audio from a (clean) TikTok URL and save it.

    TODO (you direct this): decide the return shape, options, and save location.
    """
    raise NotImplementedError
