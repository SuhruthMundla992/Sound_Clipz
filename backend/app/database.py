from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

# Read the .env file so DATABASE_URL (and friends) are available.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# The engine manages connections to Postgres.
engine = create_engine(DATABASE_URL, echo=True)


# Tables are created and changed by Alembic migrations (backend/alembic/), not here.


def get_session():
    """Open a database session for one request, and close it when the request ends.

    Used with FastAPI's Depends(): everything before `yield` runs before the
    route, and the `with` block closes the session after the route finishes.
    """
    with Session(engine) as session:
        yield session
