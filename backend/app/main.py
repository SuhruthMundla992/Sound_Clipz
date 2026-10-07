

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.pipeline import process_share


app = FastAPI(title="Sound Clipz")


# Describes the JSON body POST /clip expects:  {"url": "..."}
# FastAPI validates incoming requests against this automatically.
class ClipRequest(BaseModel):
    url: str


# @app.get("/health") maps an HTTP GET request for the URL "/health"
# to the function below. Returning a dict -> FastAPI sends it back as JSON.
@app.get("/health")
def health():
    return {"status": "ok"}


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
