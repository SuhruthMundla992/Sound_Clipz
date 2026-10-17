"""
clip.py — saving and looking up clips in the database.

Like playlist.py, each function takes a Session, and HTTP concerns (status
codes, 404s) are left to main.py.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.models import Clip


def get_clip(session: Session, clip_id: uuid.UUID) -> Clip | None:
    """Return the clip with this UUID, or None if it doesn't exist."""
    return session.get(Clip, clip_id)


def get_clip_by_video_id(session: Session, video_id: str) -> Clip | None:
    """Return the clip saved for this TikTok video id, or None. Used for dedup."""
    return session.exec(select(Clip).where(Clip.video_id == video_id)).first()


def list_clips(session: Session, offset: int = 0, limit: int = 50) -> tuple[list[Clip], int]:
    """Return a page of clips (newest first) and the total count."""
    clips = list(
        session.exec(select(Clip).order_by(Clip.created_at.desc()).offset(offset).limit(limit))
    )
    total = session.exec(select(func.count()).select_from(Clip)).one()
    return clips, total


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


def update_clip(session: Session, clip: Clip, changes: dict) -> Clip:
    """Apply only the fields in `changes` to a clip and save."""
    for field, value in changes.items():
        setattr(clip, field, value)
    session.add(clip)
    session.commit()
    session.refresh(clip)
    return clip


def delete_clip(session: Session, clip: Clip, media_root: Path) -> None:
    """Delete a clip row and its audio file from disk.

    All PlaylistClip rows referencing it are removed by the DB via cascade
    (or must be cleaned up by the caller before this is called).
    """
    audio_path = media_root / clip.file_path
    session.delete(clip)
    session.commit()
    # Remove the file after the transaction commits so we don't delete it
    # if the DB operation fails.
    if audio_path.exists():
        audio_path.unlink(missing_ok=True)
