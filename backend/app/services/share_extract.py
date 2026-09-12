"""
share_extract.py — handle the link coming in from the iOS share button.

Responsibility: take whatever the share sheet / API sends us and turn it into a
clean, canonical TikTok URL that audio_extractor.py can use.

This is the "front door" of the backend. It does NOT download anything — it just
validates and cleans the incoming link.

Typical things this file will need to handle:
  - short links (e.g. https://vm.tiktok.com/XXXX/) that redirect to the real URL
  - tracking junk in the query string (?_r=1&_t=... etc.)
  - making sure the link is actually a TikTok URL and not garbage
"""

from __future__ import annotations


def clean_share_url(raw_url: str) -> str:
    """
    Take a raw shared link and return a clean TikTok URL.

    TODO (you direct this): decide what "clean" means and implement it.
    """
    raise NotImplementedError
