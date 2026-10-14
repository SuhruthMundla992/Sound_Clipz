"""
config.py — settings that can differ from machine to machine.

Values come from the environment (the .env file) when set, with sensible
defaults for local development.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# backend/ — this file is backend/app/config.py, so go up one folder.
BACKEND_ROOT = Path(__file__).resolve().parents[1]

# The folder that holds all saved media (audio, and later cover images).
# File paths stored in the database are RELATIVE to this folder, e.g.
# "original/7675252022941060382.mp3". Moving the backend to another machine
# or into Docker only means pointing MEDIA_ROOT somewhere else.
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BACKEND_ROOT / "media")).resolve()
