from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.config import MEDIA_ROOT
from app.database import create_db_and_tables, get_session
from app.models import PlaylistClip
from app.pipeline import process_share
from app.services import clip as clip_service
from app.services import playlist as playlist_service
from app.services.audio_extractor import TikTokUnavailable


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Sound Clipz", lifespan=lifespan)


# ── Request / response body models ────────────────────────────────────────────

class ClipRequest(BaseModel):
    url: str


class PlaylistCreate(BaseModel):
    name: str = Field(min_length=1)


class PlaylistClipAdd(BaseModel):
    clip_id: uuid.UUID


# Valid repeat modes; anything else is a 422.
RepeatMode = Literal["off", "count", "one"]

# Valid sort keys and directions for playlist reordering.
SortBy        = Literal["date_added", "duration", "title"]
SortDirection = Literal["asc", "desc"]


# PATCH /playlists/{id} — send only the fields to change.
class PlaylistUpdate(BaseModel):
    name: str = Field(default=None, min_length=1)
    repeat_mode: RepeatMode = None
    repeat_count: int = Field(default=None, ge=1, le=99)
    loop_playlist: bool = None


# PATCH /playlists/{id}/clips/{clip_id} — null clears a per-song override.
class PlaylistClipUpdate(BaseModel):
    repeat_mode: RepeatMode | None = None
    repeat_count: int | None = Field(default=None, ge=1, le=99)


# POST /playlists/{id}/sort
class PlaylistSortRequest(BaseModel):
    by: SortBy
    direction: SortDirection


# ── Helpers ───────────────────────────────────────────────────────────────────

def _playlist_response(session: Session, playlist) -> dict:
    """Playlist fields + clips with their effective repeat settings."""
    songs = []
    for clip, entry in playlist_service.get_playlist_entries(session, playlist.id):
        mode, count = playlist_service.effective_repeat(playlist, entry)
        songs.append({
            **clip.model_dump(),
            "position": entry.position,
            "repeat_mode": mode,
            "repeat_count": count,
            "has_override": entry.repeat_mode is not None or entry.repeat_count is not None,
        })
    return {**playlist.model_dump(), "clips": songs}


# ── Clips ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/clips")
def list_clips(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    """List all saved clips, newest first. Supports pagination via offset/limit."""
    clips, total = clip_service.list_clips(session, offset=offset, limit=limit)
    return {"total": total, "offset": offset, "limit": limit, "items": clips}


@app.post("/clips")
def create_clip(request: ClipRequest, response: Response, session: Session = Depends(get_session)):
    """Download a TikTok and save it. 201 = new clip, 200 = already saved."""
    try:
        clip, created = process_share(session, request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TikTokUnavailable:
        raise HTTPException(
            status_code=502,
            detail="Couldn't get that TikTok. It may be deleted or private.",
        )
    response.status_code = 201 if created else 200
    return clip


@app.get("/clips/{clip_id}/audio")
def get_clip_audio(clip_id: uuid.UUID, session: Session = Depends(get_session)):
    """Stream the audio file for a clip."""
    clip = clip_service.get_clip(session, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found")
    full_path = MEDIA_ROOT / clip.file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Audio file missing")
    return FileResponse(full_path)


@app.delete("/clips/{clip_id}", status_code=204)
def delete_clip(clip_id: uuid.UUID, session: Session = Depends(get_session)):
    """Remove a clip from the library and delete its audio file.

    Also removes the clip from every playlist it belongs to and updates
    those playlists' totals.
    """
    clip = clip_service.get_clip(session, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found")

    # Remove from every playlist first so totals stay consistent.
    links = session.exec(
        select(PlaylistClip).where(PlaylistClip.clip_id == clip_id)
    ).all()
    for link in links:
        playlist_service.remove_clip_from_playlist(session, link.playlist_id, clip)

    clip_service.delete_clip(session, clip, MEDIA_ROOT)


# ── Playlists ─────────────────────────────────────────────────────────────────

@app.get("/playlists")
def list_playlists(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    """List all playlists, newest first."""
    playlists, total = playlist_service.list_playlists(session, offset=offset, limit=limit)
    return {"total": total, "offset": offset, "limit": limit, "items": playlists}


@app.post("/playlists", status_code=201)
def create_playlist(request: PlaylistCreate, session: Session = Depends(get_session)):
    return playlist_service.create_playlist(session, request.name)


@app.get("/playlists/{playlist_id}")
def get_playlist(playlist_id: int, session: Session = Depends(get_session)):
    playlist = playlist_service.get_playlist(session, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return _playlist_response(session, playlist)


@app.patch("/playlists/{playlist_id}")
def update_playlist(
    playlist_id: int, request: PlaylistUpdate, session: Session = Depends(get_session)
):
    """Change a playlist's name or playback settings. Send only the fields to update."""
    playlist = playlist_service.get_playlist(session, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    changes = request.model_dump(exclude_unset=True)
    playlist = playlist_service.update_playlist(session, playlist, changes)
    return _playlist_response(session, playlist)


@app.delete("/playlists/{playlist_id}", status_code=204)
def delete_playlist(playlist_id: int, session: Session = Depends(get_session)):
    """Delete a playlist. Clips in the library are not affected."""
    playlist = playlist_service.get_playlist(session, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    playlist_service.delete_playlist(session, playlist)


@app.post("/playlists/{playlist_id}/clips", status_code=201)
def add_clip_to_playlist(
    playlist_id: int, request: PlaylistClipAdd, session: Session = Depends(get_session)
):
    """Add a saved clip to a playlist. 409 if it's already there."""
    if playlist_service.get_playlist(session, playlist_id) is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    clip = clip_service.get_clip(session, request.clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found")

    added = playlist_service.add_clip_to_playlist(session, playlist_id, clip)
    if not added:
        raise HTTPException(status_code=409, detail="Clip is already in this playlist")

    playlist = playlist_service.get_playlist(session, playlist_id)
    return _playlist_response(session, playlist)


@app.delete("/playlists/{playlist_id}/clips/{clip_id}", status_code=204)
def remove_clip_from_playlist(
    playlist_id: int, clip_id: uuid.UUID, session: Session = Depends(get_session)
):
    """Remove a clip from a playlist. The clip stays in the library."""
    playlist = playlist_service.get_playlist(session, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    clip = clip_service.get_clip(session, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found")

    removed = playlist_service.remove_clip_from_playlist(session, playlist_id, clip)
    if not removed:
        raise HTTPException(status_code=404, detail="Clip is not in this playlist")


@app.patch("/playlists/{playlist_id}/clips/{clip_id}")
def update_playlist_clip(
    playlist_id: int,
    clip_id: uuid.UUID,
    request: PlaylistClipUpdate,
    session: Session = Depends(get_session),
):
    """Set or clear a per-song repeat override. Send null to clear a field."""
    playlist = playlist_service.get_playlist(session, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    entry = playlist_service.get_playlist_entry(session, playlist_id, clip_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Clip is not in this playlist")
    playlist_service.update_playlist_entry(session, entry, request.model_dump(exclude_unset=True))
    return _playlist_response(session, playlist)


@app.post("/playlists/{playlist_id}/sort")
def sort_playlist(
    playlist_id: int,
    request: PlaylistSortRequest,
    session: Session = Depends(get_session),
):
    """Re-order a playlist's clips in place.

    `by` choices:
    - `date_added` — when the clip was added to this playlist
    - `duration`   — length of the audio clip (shortest or longest first)
    - `title`      — alphabetical by clip title

    `direction`: `asc` or `desc` (e.g. title asc = A→Z, title desc = Z→A;
    date_added desc = most recently added first).
    """
    playlist = playlist_service.get_playlist(session, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    try:
        playlist_service.sort_playlist(session, playlist_id, request.by, request.direction)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return _playlist_response(session, playlist)
