"""
clip.py — saving and looking up clips in the database.

Like playlist.py, each function takes a Session, and HTTP concerns (status
codes, 404s) are left to main.py.
"""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import Clip


def get_clip(session: Session, clip_id: uuid.UUID) -> Clip | None:
    """Return the clip with this UUID, or None if it doesn't exist."""
    return session.get(Clip, clip_id)


def get_clip_by_video_id(session: Session, video_id: str) -> Clip | None:
    """Return the clip saved for this TikTok video id, or None. Used for dedup."""
    return session.exec(select(Clip).where(Clip.video_id == video_id)).first()


def save_clip(session: Session, video_id: str, file_path: str, metadata: dict) -> Clip:
    """Save a new Clip row and return it."""
    clip = Clip(
        video_id=video_id,
        file_path=file_path,
        title=metadata["title"],
        uploader=metadata["uploader"],
        duration=metadata["duration"],
        thumbnail=metadata["thumbnail"],
    )
    session.add(clip)
    try:
        session.commit()
    except IntegrityError:
        # Safety net: video_id is unique, so if another server process saved
        # this TikTok a moment ago, Postgres refuses ours. Return theirs instead.
        session.rollback()
        return get_clip_by_video_id(session, video_id)
    session.refresh(clip)
    return clip
