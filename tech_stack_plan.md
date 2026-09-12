# Python Backend — Full Tech Stack, Sound Quality & Storage

## 1. Python backend — the technology stack

| Job | Technology | Why this one |
|---|---|---|
| **Web/API framework** | **FastAPI** + **Uvicorn** | Async, fast, auto-generates API docs, tiny code. The standard for this. |
| **TikTok extraction** ⭐ | **yt-dlp** (library, not just CLI) | *The* tool for pulling media from TikTok. Handles the link→media problem for you. Actively maintained. |
| **Audio processing** | **FFmpeg** (via `ffmpeg-python` or subprocess) | Industry-standard. Does extraction, format conversion, loudness, filtering — everything. |
| **Metadata / tags** | **Mutagen** | Reads/writes title, artist, cover art into the audio files so your Spotify-like app shows them nicely. |
| **Database** | **SQLite** (via SQLModel/SQLAlchemy) | Stores clip records + playlists. Zero setup, one file. Upgrade to Postgres only if you ever go multi-user. |
| **Background jobs** | **FastAPI BackgroundTasks** (start) → **Celery + Redis** (later) | Downloading takes a few seconds — you don't want the phone waiting. Start simple, add a real queue only if needed. |
| **Serving audio** | FastAPI `FileResponse` / `StreamingResponse` | Streams the mp3 to the app with seek support. |
| Optional later | **MinIO** (S3-compatible) | Only if you move files off local disk. |

**No external paid APIs needed.** No TikTok API key, no cloud service required. yt-dlp + FFmpeg
do the heavy lifting locally and free. That's a deliberate choice — it keeps you off
fragile/paid third-party resolver services.

**`requirements.txt` will basically be:**

```
fastapi
uvicorn[standard]
yt-dlp
ffmpeg-python
mutagen
sqlmodel
```

## 2. Sound integrity — the honest version + how to actually improve it

**The hard truth first:** TikTok's audio is already **lossy** (AAC, usually ~128 kbps). You
**cannot** recover quality that isn't in the source — no tool "adds back" detail that was thrown
away. Anyone promising true quality *increase* is selling snake oil.

**But here's what you genuinely CAN do — and it matters a lot:**

### a) Preserve, don't degrade (integrity)

The #1 mistake is re-encoding lossy→lossy and losing quality *again*. Avoid it:

- Have yt-dlp grab the **best available audio stream**.
- **Copy the audio stream without re-encoding** when possible — FFmpeg `-c:a copy`
  (or yt-dlp `--remux`). This keeps TikTok's original AAC bytes → **zero generational loss**.
- Store the result as **`.m4a` (AAC)** rather than converting to MP3. It's native to iPhone,
  and skips a needless lossy conversion. (MP3 only if you specifically want it.)

### b) Make it *sound* better (real, audible wins)

You can't add information, but you can make clips more pleasant and consistent:

| Improvement | Tool (FFmpeg filter) | Impact |
|---|---|---|
| **Loudness normalization** ⭐ | `loudnorm` (EBU R128, two-pass) | **Biggest win.** Every clip plays at the same, comfortable volume — no more one clip blasting, next one silent. Essential for a playlist. |
| **Remove rumble/hum** | `highpass=f=80` | Cleans muddy low-end. |
| **Noise reduction** | `afftdn` or `arnndn` (RNNoise) | Helps noisy/spoken clips; use gently. |
| **Gentle limiting** | `alimiter` | Stops clipping/distortion peaks. |
| **De-esser / light EQ** | `equalizer` | Optional polish. |

So the processing recipe is: **extract → (copy stream if clean) → loudness-normalize →
light cleanup → tag with metadata**. Keep it optional/toggleable per clip.

### c) Keep the original

Always save the untouched extraction *and* the processed version. If a filter ever makes
something worse, you still have the pristine copy. Cheap insurance (audio files are small).

## 3. Where the files are stored

**Recommended default — local disk on wherever the backend runs (your Mac / Raspberry Pi /
small VPS):**

```
backend/
├── media/
│   ├── original/           # untouched extraction (safety copy)
│   │   └── {clip_id}.m4a
│   └── processed/          # normalized/cleaned version the app plays
│       └── {clip_id}.m4a
├── covers/                 # thumbnail / cover images
│   └── {clip_id}.jpg
└── soundclipz.db           # SQLite: metadata + which file is where
```

- **SQLite holds the *metadata*** (title, source URL, duration, dates, playlist membership) and
  a **path pointer** to each file. Files themselves stay on disk — you never store binary blobs
  in the DB.
- Clips are tiny (a 30-sec clip ≈ 0.5–1 MB), so even thousands fit in a couple GB.

**Storage options compared:**

| Option | When | Tradeoff |
|---|---|---|
| **Local disk** (recommended start) | Backend on a home computer/Pi | Simplest, fastest, free. Must keep that machine reachable. |
| **External drive / NAS** | Big library, home setup | More space, still simple. |
| **Object storage** (MinIO self-host, or Backblaze B2 / S3) | You want it accessible anywhere without a home server | More setup + tiny cost; scales infinitely; good for a VPS deploy. |

**My recommendation:** start with **local disk + SQLite**. Keep the storage layer behind one
module (`storage/files.py`) so if you later want to move to S3/MinIO, you swap that one file and
nothing else changes.

## Quick recap of the decisions

- **Stack:** FastAPI + yt-dlp + FFmpeg + Mutagen + SQLite. No paid APIs.
- **Quality:** can't beat the source, but **copy-don't-reencode** + **loudness normalization**
  gives you clean, consistent, integrity-preserving audio (store as `.m4a`, keep the original).
- **Storage:** local disk for the files, SQLite for metadata, behind a swappable storage module.
