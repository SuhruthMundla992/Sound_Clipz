"""
playlist.py — playlist operations (the database work behind the /playlists routes).

Each function takes a Session so that one request uses one conversation with
the database. main.py handles HTTP concerns (status codes, 404s); this file
only knows about playlists and the database.
"""

from __future__ import annotations

import uuid

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


def update_playlist(session: Session, playlist: Playlist, changes: dict) -> Playlist:
    """Apply only the fields in `changes` (e.g. {"repeat_mode": "one"}) and save."""
    for field, value in changes.items():
        setattr(playlist, field, value)
    session.add(playlist)
    session.commit()
    session.refresh(playlist)
    return playlist


def get_playlist_entries(session: Session, playlist_id: int) -> list[tuple[Clip, PlaylistClip]]:
    """Return (clip, link row) pairs for a playlist, in the order they were added.

    The link row comes along because it holds each song's repeat override.
    """
    statement = (
        select(Clip, PlaylistClip)
        .join(PlaylistClip, PlaylistClip.clip_id == Clip.id)
        .where(PlaylistClip.playlist_id == playlist_id)
        .order_by(PlaylistClip.added_at)
    )
    return list(session.exec(statement))


def get_playlist_entry(session: Session, playlist_id: int, clip_id: uuid.UUID) -> PlaylistClip | None:
    """Return the link row for this clip in this playlist, or None if it isn't in it."""
    # PlaylistClip's primary key is two columns, so get() takes both.
    return session.get(PlaylistClip, {"playlist_id": playlist_id, "clip_id": clip_id})


def update_playlist_entry(session: Session, entry: PlaylistClip, changes: dict) -> PlaylistClip:
    """Set or clear one song's repeat override. A value of None clears that field."""
    for field, value in changes.items():
        setattr(entry, field, value)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def effective_repeat(playlist: Playlist, entry: PlaylistClip) -> tuple[str, int]:
    """The repeat settings that actually apply to one song in a playlist.

    Each field uses the song's override if it has one, otherwise the playlist's.
    """
    mode = entry.repeat_mode if entry.repeat_mode is not None else playlist.repeat_mode
    count = entry.repeat_count if entry.repeat_count is not None else playlist.repeat_count
    return mode, count


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
