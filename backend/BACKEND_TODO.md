# Backend To-Do (before the iPhone app)

Findings from a full review of `backend/`. Nothing here is implemented yet.

## 🔴 Fix before the frontend connects

- [ ] **1. URL check can be bypassed (SSRF).**
  `get_tiktok_url` only checks that the text `tiktok.com` appears somewhere in the URL.
  These all pass today:
  `https://evil.example/download?ref=tiktok.com`, `https://tiktok.com.evil.example/file.mp3`,
  `http://192.168.1.1/admin?tiktok.com`, `http://169.254.169.254/latest/meta-data/?tiktok.com`.
  yt-dlp then downloads from them (it has a "generic" extractor that fetches any URL), so
  anyone who can reach the API can make the server download any file or probe the local network.
  **Fix:** check the parsed hostname is `tiktok.com` or ends in `.tiktok.com` (and require https),
  and restrict yt-dlp to its TikTok extractors (`allowed_extractors`).

- [ ] **2. No authentication.**
  Anyone who can reach the server can create clips, edit or empty playlists, and stream audio.
  OK on home Wi-Fi; required before the server is reachable from the internet.
  **Fix:** start with a secret API key header checked on every request; add user accounts later.

- [ ] **3. Postgres isn't migrated yet.**
  Playlist endpoints will fail against Postgres until the repeat columns exist.
  **Fix (from `backend/`, with Postgres running):**
  `.venv/bin/alembic stamp 0001` then `.venv/bin/alembic upgrade head`.
  Check with `.venv/bin/alembic current` → `0002 (head)`.

- [ ] **4. Endpoints the app needs that don't exist yet.**
  - `GET /playlists` — list all playlists (home screen)
  - `GET /clips` — list all saved clips (library / pick a clip to add)
  - `DELETE /playlists/{id}/clips/{clip_id}` — remove a song; must subtract from `clip_count` and `total_duration` in the same transaction
  - `DELETE /playlists/{id}` — delete a playlist (and its link rows)

- [ ] **5. Thumbnail URLs expire.**
  `Clip.thumbnail` stores TikTok's image URL, which contains `x-expires=...` and stops working
  within days, so cover art will break.
  **Fix:** download the image into `media/covers/` when saving a clip, store a relative path,
  and serve it from `GET /clips/{id}/thumbnail`.

- [ ] **6. No download timeout.**
  If TikTok stops responding mid-download, the request never finishes and keeps holding that
  video's lock, so later shares of the same TikTok hang too.
  **Fix:** set yt-dlp's `socket_timeout` (e.g. 30 seconds).

## 🟡 Backend ↔ app contract

- [ ] **7. Inconsistent response shapes.**
  `POST /playlists` returns no `clips` list, while GET, PATCH, and add-clip do.
  `POST /clips` returns `file_path` (an internal detail) instead of something the app can use,
  like an `audio_url`.
  **Fix:** declare FastAPI response models so every endpoint has one exact shape, shown on `/docs`.

- [ ] **8. Date format will break Swift decoding.**
  Timestamps include fractional seconds (`...07:56:48.001417+00:00`) and sometimes end in `Z`
  instead of `+00:00`. Swift's built-in `.iso8601` decoding fails on fractional seconds.
  **Fix:** a custom date decoder in Swift, or a single consistent format from the backend.

- [ ] **9. The phone can't reach the server as currently run.**
  - `uvicorn` listens on `127.0.0.1` only. Run with `--host 0.0.0.0` and have the app use the
    Mac's local IP (e.g. `http://192.168.1.20:8000`).
  - iOS blocks plain `http://` by default (App Transport Security). Use the
    `NSAllowsLocalNetworking` exception for local testing; HTTPS for real use.

## 🟢 Cleanup / later

- [ ] **10.** `echo=True` in `database.py` logs every SQL statement. Make it a setting (off by default).
- [ ] **11.** `share_extract.py` imports `requests`, `os`, `pathlib` but uses none. `requests` isn't
  in `requirements.txt` (it only works because yt-dlp installs it), so a future yt-dlp change
  could stop the server from starting. Remove them, plus the leftover `main()` test function.
- [ ] **12.** Pin exact versions in `requirements.txt`. The working setup uses a nightly yt-dlp;
  a fresh install would get the regular release.
- [ ] **13.** Each download holds a database connection for its whole duration; ~15 at once would
  exhaust the pool. Fine for one user; background jobs (Celery + Redis) fix it later.
- [ ] **14.** `_video_locks` in `pipeline.py` keeps one lock per video forever. Small, but unbounded.
- [ ] **15.** Re-sharing a TikTok that's since been deleted returns 502 even if it's already saved,
  because TikTok is asked for the video id first.

## Suggested order
1, 3, 4, 6 first (small, needed right away) → 5 and 7 (before writing the Swift screens)
→ 2 (before going on the internet) → the rest.
