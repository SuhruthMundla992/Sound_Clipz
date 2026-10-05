
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit
import requests
import os
import pathlib

def get_tiktok_url(raw_url: str) -> str:


    # check if the URL is a valid TikTok URL

    if "tiktok.com" not in raw_url:
        raise ValueError("Invalid TikTok URL")
    


    return clean_share_url(raw_url)
    
    
    




def clean_share_url(raw_url: str) -> str:

    parts = urlsplit(raw_url)




    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def main():

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