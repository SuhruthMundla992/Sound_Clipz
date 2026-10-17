

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.config import MEDIA_ROOT
from app.database import get_session
from app.pipeline import process_share
from app.services import clip as clip_service
from app.services import playlist as playlist_service
from app.services.audio_extractor import TikTokUnavailable


# The database tables are created and changed by Alembic migrations, not by the
# app. Before starting the server, bring the database up to date (from backend/):
#     .venv/bin/alembic upgrade head
app = FastAPI(title="Sound Clipz")


# Describes the JSON body POST /clips expects:  {"url": "..."}
# FastAPI validates incoming requests against this automatically.
class ClipRequest(BaseModel):
    url: str


# Body for POST /playlists:  {"name": "Gym Beats"}
# min_length=1 rejects an empty name with a 422.
class PlaylistCreate(BaseModel):
    name: str = Field(min_length=1)


# Body for POST /playlists/{playlist_id}/clips:  {"clip_id": "<uuid>"}
class PlaylistClipAdd(BaseModel):
    clip_id: uuid.UUID


# The only allowed repeat modes. Anything else is rejected with a 422.
RepeatMode = Literal["off", "count", "one"]


# Body for PATCH /playlists/{playlist_id}. Send only the fields to change,
# e.g. {"repeat_mode": "count", "repeat_count": 3}. Leaving a field out keeps
# its current value. The types aren't `| None`, so sending null is a 422
# (a playlist must always have a name, a mode, etc.).
class PlaylistUpdate(BaseModel):
    name: str = Field(default=None, min_length=1)
    repeat_mode: RepeatMode = None
    repeat_count: int = Field(default=None, ge=1, le=99)
    loop_playlist: bool = None


# Body for PATCH /playlists/{playlist_id}/clips/{clip_id}: one song's override.
# Here null IS allowed: {"repeat_mode": null} clears the override so the song
# goes back to following the playlist's setting.
class PlaylistClipUpdate(BaseModel):
    repeat_mode: RepeatMode | None = None
    repeat_count: int | None = Field(default=None, ge=1, le=99)


def _playlist_response(session: Session, playlist) -> dict:
    """A playlist's fields plus its songs, each with the repeat settings that apply to it."""
    songs = []
    for clip, entry in playlist_service.get_playlist_entries(session, playlist.id):
        mode, count = playlist_service.effective_repeat(playlist, entry)
        songs.append({
            **clip.model_dump(),
            "repeat_mode": mode,
            "repeat_count": count,
            # True when this song has its own setting instead of the playlist's.
            "has_override": entry.repeat_mode is not None or entry.repeat_count is not None,
        })
    return {**playlist.model_dump(), "clips": songs}


# @app.get("/health") maps an HTTP GET request for the URL "/health"
# to the function below. Returning a dict -> FastAPI sends it back as JSON.
@app.get("/health")
def health():
    return {"status": "ok"}


#


# POST /clips — the real endpoint. Takes a TikTok URL, runs the pipeline.
# Regular `def` (not async) because process_share is blocking.
@app.post("/clips")
def create_clip(request: ClipRequest, response: Response, session: Session = Depends(get_session)):
    try:
        clip, created = process_share(session, request.url)
    except ValueError as e:
        # Bad/invalid link -> return a clean HTTP 400 instead of a 500 crash.
        raise HTTPException(status_code=400, detail=str(e))
    except TikTokUnavailable:
        # TikTok wouldn't give us the video. 502 = "a service we depend on
        # failed", which tells the app this isn't a bug in our server.
        raise HTTPException(
            status_code=502,
            detail="Couldn't get that TikTok. It may be deleted or private.",
        )
    # 201 = downloaded and saved just now; 200 = it was already in the library.
    response.status_code = 201 if created else 200
    return clip


# GET /clips/{clip_id}/audio — stream a clip's audio file (what the phone plays).
# Path: clip UUID -> clip row -> file_path -> MEDIA_ROOT / file_path -> the file.
@app.get("/clips/{clip_id}/audio")
def get_clip_audio(clip_id: uuid.UUID, session: Session = Depends(get_session)):
    clip = clip_service.get_clip(session, clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found")
    full_path = MEDIA_ROOT / clip.file_path
    if not full_path.exists():
        # The row exists but the file was deleted from disk.
        raise HTTPException(status_code=404, detail="Audio file missing")
    return FileResponse(full_path)


# POST /playlists — create a new playlist.
# status_code=201 means "Created", the REST convention for a successful POST.
@app.post("/playlists", status_code=201)
def create_playlist(request: PlaylistCreate, session: Session = Depends(get_session)):
    return playlist_service.create_playlist(session, request.name)


# GET /playlists/{playlist_id} — read one playlist and the clips inside it.
@app.get("/playlists/{playlist_id}")
def get_playlist(playlist_id: int, session: Session = Depends(get_session)):
    playlist = playlist_service.get_playlist(session, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return _playlist_response(session, playlist)


# POST /playlists/{playlist_id}/clips — add a saved clip to a playlist.
@app.post("/playlists/{playlist_id}/clips", status_code=201)
def add_clip_to_playlist(
    playlist_id: int, request: PlaylistClipAdd, session: Session = Depends(get_session)
):
    if playlist_service.get_playlist(session, playlist_id) is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    clip = clip_service.get_clip(session, request.clip_id)
    if clip is None:
        raise HTTPException(status_code=404, detail="Clip not found")

    added = playlist_service.add_clip_to_playlist(session, playlist_id, clip)
    if not added:
        # 409 Conflict: the request is valid, but clashes with what's already there.
        raise HTTPException(status_code=409, detail="Clip is already in this playlist")

    # Return the updated playlist (new totals) with its clips, same shape as GET.
    playlist = playlist_service.get_playlist(session, playlist_id)
    return _playlist_response(session, playlist)


# PATCH /playlists/{playlist_id} — change a playlist's name or playback settings.
# PATCH = "update part of it": only the fields sent are changed.
@app.patch("/playlists/{playlist_id}")
def update_playlist(
    playlist_id: int, request: PlaylistUpdate, session: Session = Depends(get_session)
):
    playlist = playlist_service.get_playlist(session, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    # exclude_unset=True keeps only the fields the client actually sent.
    changes = request.model_dump(exclude_unset=True)
    playlist = playlist_service.update_playlist(session, playlist, changes)
    return _playlist_response(session, playlist)


# PATCH /playlists/{playlist_id}/clips/{clip_id} — set or clear one song's
# repeat override inside this playlist.
@app.patch("/playlists/{playlist_id}/clips/{clip_id}")
def update_playlist_clip(
    playlist_id: int,
    clip_id: uuid.UUID,
    request: PlaylistClipUpdate,
    session: Session = Depends(get_session),
):
    playlist = playlist_service.get_playlist(session, playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    entry = playlist_service.get_playlist_entry(session, playlist_id, clip_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Clip is not in this playlist")
    playlist_service.update_playlist_entry(session, entry, request.model_dump(exclude_unset=True))
    return _playlist_response(session, playlist)
