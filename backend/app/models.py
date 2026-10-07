"""
models.py — the database tables, defined as Python classes (SQLModel).

Each class with `table=True` becomes a real table in Postgres.
A row = an instance of the class; a column = an attribute.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import SQLModel, Field


class Clip(SQLModel, table=True):
    """One extracted audio clip + its metadata (the file itself lives on disk)."""

    # Primary key: a unique id for each row. Starts as None; Postgres fills it
    # in automatically when the row is inserted (auto-incrementing).
    id: int | None = Field(default=None, primary_key=True)

    # TikTok's own video id. unique=True -> the DB refuses duplicates (dedup!).
    # index=True -> makes looking up a clip by video_id fast.
    video_id: str = Field(index=True, unique=True)

    # Metadata we got from yt-dlp.
    title: str
    uploader: str
    duration: int | None = None          # seconds; optional
    thumbnail: str | None = None         # cover image URL; optional

    # The pointer to the actual audio file on disk.
    file_path: str

    # When this row was created. default_factory runs the function at insert time.
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
