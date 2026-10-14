"""
playlist.py — playlist operations (the database work behind the /playlists routes).

Each function takes a Session so that one request uses one conversation with
the database. main.py handles HTTP concerns (status codes, 404s); this file
only knows about playlists and the database.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select, update

from app.models import Clip, Playlist, PlaylistClip


def create_playlist(session: Session, name: str) -> Playlist:
    """Save a new, empty playlist and return it with its database-assigned id."""
    playlist = Playlist(name=name)
    session.add(playlist)
    session.commit()
    session.refresh(playlist)
    return playlist


def get_playlist(session: Session, playlist_id: int) -> Playlist | None:
    """Return the playlist with this id, or None if it doesn't exist."""
    return session.get(Playlist, playlist_id)


def get_playlist_clips(session: Session, playlist_id: int) -> list[Clip]:
    """Return the clips in a playlist, in the order they were added."""
    statement = (
        select(Clip)
        .join(PlaylistClip, PlaylistClip.clip_id == Clip.id)
        .where(PlaylistClip.playlist_id == playlist_id)
        .order_by(PlaylistClip.added_at)
    )
    return list(session.exec(statement))


def add_clip_to_playlist(session: Session, playlist_id: int, clip: Clip) -> bool:
    """Add a clip to a playlist and update the playlist's totals, in one transaction.

    Returns False (and changes nothing) if the clip is already in the playlist.
    The caller should check that the playlist and clip exist first.
    """
    try:
        # 1. The link row: "this clip is in this playlist".
        session.add(PlaylistClip(playlist_id=playlist_id, clip_id=clip.id))

        # 2. The totals. Postgres does the adding (SET clip_count = clip_count + 1)
        #    instead of Python reading the number and writing it back, so two clips
        #    added at the same moment can't overwrite each other's update.
        #    Running this also sends the link row from step 1 to Postgres first,
        #    which is why a duplicate can be refused here, inside the try.
        session.exec(
            update(Playlist)
            .where(Playlist.id == playlist_id)
            .values(
                clip_count=Playlist.clip_count + 1,
                total_duration=Playlist.total_duration + (clip.duration or 0),
            )
        )
        session.commit()
    except IntegrityError:
        # The (playlist_id, clip_id) primary key refused a duplicate link.
        # rollback() undoes BOTH steps, so the totals don't change either.
        session.rollback()
        return False
    return True
