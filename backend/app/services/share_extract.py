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

from urllib.parse import urlsplit, urlunsplit
import requests
import os
import pathlib

def get_tiktok_url(raw_url: str) -> str:
    

    """
    Take a raw shared link and return a clean TikTok URL.

    This is the main entry point for the share_extract module.
    """


def clean_share_url(raw_url: str) -> str:
    """
    Strip the tracking junk off a TikTok link.

    Keeps the meaningful parts of the URL (scheme, host, path) and drops the
    query string (?_r=1&_t=...) and any #fragment. We never look for specific
    params to remove -- we keep what we want and discard the rest.

    Example:
        https://www.tiktok.com/@user/video/7412...?_r=1&_t=ZP-99...
        -> https://www.tiktok.com/@user/video/7412...
    """
    parts = urlsplit(raw_url)



    # urlunsplit takes a 5-tuple: (scheme, netloc, path, query, fragment).
    # Blank out query + fragment; keep the rest.
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def main():
    """
    Run some quick tests on the share_extract module.
    """
    test_urls = [
        "https://www.tiktok.com/t/ZP83af6pe/",
        "https://www.tiktok.com/@user/video/7412...?_r=1&_t=ZP-99...",
        "https://vm.tiktok.com/XXXX/",
        "https://www.tiktok.com/@user/video/7412...#fragment",
        "https://www.tiktok.com/@user/video/7412...?_r=1&_t=ZP-99...#fragment",
    ]

    for url in test_urls:
        clean_url = clean_share_url(url)
        print(f"Raw: {url}\nClean: {clean_url}\n")


if __name__ == "__main__":
    main()