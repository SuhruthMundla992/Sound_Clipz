"""
models.py — the database tables, defined as Python classes (SQLModel).

Each class with `table=True` becomes a real table in Postgres.
A row = an instance of the class; a column = an attribute.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field


class Clip(SQLModel, table=True):
    """One extracted audio clip + its metadata (the file itself lives on disk)."""

    # Primary key: a random UUID, generated in Python the moment a Clip object is
    # created (so it exists before saving). Unguessable, unlike 1, 2, 3...
    # Note: a UUID does NOT dedupe; the same TikTok saved twice would get two
    # different UUIDs. video_id below is what catches duplicates.
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # TikTok's own video id. unique=True -> the DB refuses duplicates (dedup!).
    # index=True -> makes looking up a clip by video_id fast.
    video_id: str = Field(index=True, unique=True)

    # Metadata we got from yt-dlp.
    title: str
    uploader: str
    duration: int | None = None          # seconds; optional
    thumbnail: str | None = None         # cover image URL; optional

    # The pointer to the actual audio file on disk, RELATIVE to MEDIA_ROOT
    # (e.g. "original/7675252022941060382.mp3"). Full path = MEDIA_ROOT / file_path.
    file_path: str

    # When this row was created. default_factory runs the function at insert time.
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Playlist(SQLModel, table=True):
    """A named collection of clips. Which clips it holds lives in PlaylistClip."""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Stored totals so reading a playlist is fast. These must be updated
    # whenever a clip is added to or removed from the playlist.
    clip_count: int = 0
    total_duration: int = 0  # seconds, sum of every clip's duration

    # Playback settings. The backend only stores these; the phone's player
    # follows them when a song ends.
    #   "off"   -> play each song once, then the next
    #   "count" -> play each song repeat_count times, then the next
    #   "one"   -> repeat the current song until it's skipped
    repeat_mode: str = "off"
    repeat_count: int = 1
    # After the last song: True = start over from the first, False = stop.
    loop_playlist: bool = False


class PlaylistClip(SQLModel, table=True):
    """Link table: one row per (playlist, clip) pair.

    This is what lets a playlist hold many clips and a clip appear in many
    playlists (a many-to-many relationship).
    """

    # Both columns together form the primary key, so the same clip can't be
    # added to the same playlist twice.
    playlist_id: int = Field(foreign_key="playlist.id", primary_key=True)
    clip_id: uuid.UUID = Field(foreign_key="clip.id", primary_key=True)
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Optional per-song override of the playlist's repeat settings.
    # None means "use the playlist's setting"; each field falls back on its own.
    repeat_mode: str | None = None
    repeat_count: int | None = None
