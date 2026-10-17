"""
playlist.py — playlist operations (the database work behind the /playlists routes).

Each function takes a Session so that one request uses one conversation with
the database. main.py handles HTTP concerns (status codes, 404s); this file
only knows about playlists and the database.
"""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select, update

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


def list_playlists(session: Session, offset: int = 0, limit: int = 50) -> tuple[list[Playlist], int]:
    """Return a page of playlists (newest first) and the total count."""
    playlists = list(
        session.exec(
            select(Playlist).order_by(Playlist.created_at.desc()).offset(offset).limit(limit)
        )
    )
    total = session.exec(select(func.count()).select_from(Playlist)).one()
    return playlists, total


def update_playlist(session: Session, playlist: Playlist, changes: dict) -> Playlist:
    """Apply only the fields in `changes` (e.g. {"repeat_mode": "one"}) and save."""
    for field, value in changes.items():
        setattr(playlist, field, value)
    session.add(playlist)
    session.commit()
    session.refresh(playlist)
    return playlist


def delete_playlist(session: Session, playlist: Playlist) -> None:
    """Delete a playlist and all its link rows. Clips themselves are untouched."""
    session.delete(playlist)
    session.commit()


def get_playlist_entries(session: Session, playlist_id: int) -> list[tuple[Clip, PlaylistClip]]:
    """Return (clip, link row) pairs for a playlist, sorted by position.

    The link row comes along because it holds each song's repeat override and position.
    """
    statement = (
        select(Clip, PlaylistClip)
        .join(PlaylistClip, PlaylistClip.clip_id == Clip.id)
        .where(PlaylistClip.playlist_id == playlist_id)
        .order_by(PlaylistClip.position, PlaylistClip.added_at)
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
    # Current clip_count becomes the new clip's position (0-indexed, appended to end).
    current_count = session.exec(
        select(func.count()).select_from(PlaylistClip).where(PlaylistClip.playlist_id == playlist_id)
    ).one()

    try:
        session.add(PlaylistClip(playlist_id=playlist_id, clip_id=clip.id, position=current_count))

        # Postgres does the arithmetic server-side so concurrent inserts don't race.
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
        session.rollback()
        return False
    return True


def remove_clip_from_playlist(session: Session, playlist_id: int, clip: Clip) -> bool:
    """Remove a clip from a playlist and update totals.

    Returns False if the clip wasn't in the playlist.
    Re-numbers positions so there are no gaps after the removed song.
    """
    entry = get_playlist_entry(session, playlist_id, clip.id)
    if entry is None:
        return False

    removed_position = entry.position

    session.delete(entry)
    session.exec(
        update(Playlist)
        .where(Playlist.id == playlist_id)
        .values(
            clip_count=Playlist.clip_count - 1,
            total_duration=Playlist.total_duration - (clip.duration or 0),
        )
    )
    session.commit()

    # Shift every song after the removed one down by one to close the gap.
    remaining = session.exec(
        select(PlaylistClip)
        .where(PlaylistClip.playlist_id == playlist_id)
        .where(PlaylistClip.position > removed_position)
    ).all()
    for row in remaining:
        row.position -= 1
        session.add(row)
    session.commit()

    return True


# Valid sort keys mapped to the SQLModel column expression to order by.
_SORT_COLUMNS = {
    "date_added": PlaylistClip.added_at,
    "duration":   Clip.duration,
    "title":      Clip.title,
}


def sort_playlist(
    session: Session,
    playlist_id: int,
    by: str,
    direction: str,
) -> bool:
    """Re-number the positions of every song in a playlist according to a sort.

    `by`        — one of "date_added", "duration", "title"
    `direction` — "asc" or "desc"

    Returns False if the playlist doesn't exist.
    """
    sort_col = _SORT_COLUMNS.get(by)
    if sort_col is None:
        raise ValueError(f"Unknown sort key: {by!r}")

    ordered_col = sort_col.asc() if direction == "asc" else sort_col.desc()

    # Fetch (PlaylistClip, Clip) pairs in the requested order.
    rows = list(
        session.exec(
            select(PlaylistClip, Clip)
            .join(Clip, Clip.id == PlaylistClip.clip_id)
            .where(PlaylistClip.playlist_id == playlist_id)
            .order_by(ordered_col)
        )
    )

    for new_pos, (link, _clip) in enumerate(rows):
        link.position = new_pos
        session.add(link)

    session.commit()
    return True
