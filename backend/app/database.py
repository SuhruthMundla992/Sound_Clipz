"""
database.py — the connection to Postgres.

The "engine" is the live connection pool to the database. A "session" is a
single conversation with the DB (where you add/query/commit rows).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

# Read the .env file so DATABASE_URL (and friends) are available.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# The engine manages connections to Postgres.
# echo=True prints the SQL it runs — great for learning (turn off later).
engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables() -> None:
    """Create every table defined by our SQLModel classes (if not already there)."""
    # Importing models registers them with SQLModel.metadata so create_all sees them.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Open a new database session (one conversation with the DB)."""
    return Session(engine)
