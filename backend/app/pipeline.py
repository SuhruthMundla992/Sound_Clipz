from app.services.share_extract import get_tiktok_url
from app.services.audio_extractor import extract_audio


def process_share(raw_url: str):
    #Take a raw shared TikTok link, clean it, extract the audio, return the result."""
    clean_url = get_tiktok_url(raw_url)
    result = extract_audio(clean_url)
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.pipeline <tiktok_url>")
        raise SystemExit(1)

    result = process_share(sys.argv[1])
    print(result)
