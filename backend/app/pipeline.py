import threading

from sqlmodel import Session

from app.models import Clip
from app.services import clip as clip_service
from app.services.audio_extractor import download_audio, fetch_info
from app.services.share_extract import get_tiktok_url

# One lock per TikTok video id. If the same TikTok is shared twice at the same
# moment, the second request waits on this lock until the first has finished
# downloading and saving, then finds the saved clip instead of downloading
# again. Different TikToks get different locks, so they never wait on each other.
# These locks live in this server's memory, so they only line up requests
# within one running server process.
_video_locks: dict[str, threading.Lock] = {}


def _lock_for(video_id: str) -> threading.Lock:
    # setdefault is atomic, so two requests for the same video always get the same lock.
    return _video_locks.setdefault(video_id, threading.Lock())


def process_share(session: Session, raw_url: str) -> tuple[Clip, bool]:
    """Take a raw shared TikTok link and return (clip, created).

    created is False when the TikTok was already saved; nothing is downloaded then.
    """
    clean_url = get_tiktok_url(raw_url)
    info = fetch_info(clean_url)          # metadata only, no download yet
    video_id = info["id"]

    with _lock_for(video_id):
        existing = clip_service.get_clip_by_video_id(session, video_id)
        if existing is not None:
            return existing, False

        result = download_audio(info)
        clip = clip_service.save_clip(session, video_id, result["file_path"], result["metadata"])
        return clip, True


if __name__ == "__main__":
    import sys

    from app.database import engine

    if len(sys.argv) != 2:
        print("Usage: python -m app.pipeline <tiktok_url>")
        raise SystemExit(1)

    # The tables must already exist: run `alembic upgrade head` first.
    with Session(engine) as session:
        clip, created = process_share(session, sys.argv[1])
        print("new clip saved" if created else "already saved", clip)
