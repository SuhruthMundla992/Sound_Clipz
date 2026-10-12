

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.database import create_db_and_tables
from app.pipeline import process_share


# Runs once when the server starts (before the `yield`) and once when it
# shuts down (after the `yield`).
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to the database and create any tables that don't exist yet.
    # Existing tables and their data are left untouched.
    create_db_and_tables()
    yield


app = FastAPI(title="Sound Clipz", lifespan=lifespan)


# Describes the JSON body POST /clip expects:  {"url": "..."}
# FastAPI validates incoming requests against this automatically.
class ClipRequest(BaseModel):
    url: str


# @app.get("/health") maps an HTTP GET request for the URL "/health"
# to the function below. Returning a dict -> FastAPI sends it back as JSON.
@app.get("/health")
def health():
    return {"status": "ok"}


#


# POST /clip — the real endpoint. Takes a TikTok URL, runs the pipeline.
# Regular `def` (not async) because process_share is blocking.
@app.post("/clip")
def create_clip(request: ClipRequest):
    try:
        result = process_share(request.url)
    except ValueError as e:
        # Bad/invalid link -> return a clean HTTP 400 instead of a 500 crash.
        raise HTTPException(status_code=400, detail=str(e))
    return result


# POST /playlists — create a new playlist.
@app.post("/playlists")
def create_playlist():
    pass


# GET /playlists/{playlist_id} — read one playlist by its id.
@app.get("/playlists/{playlist_id}")
def get_playlist(playlist_id: int):
    pass
