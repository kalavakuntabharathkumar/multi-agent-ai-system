# SQLAlchemy database setup: engine, session factory, and declarative base.
# All models inherit from Base; get_db() is injected as a FastAPI dependency.

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read the database connection URL from the environment (required at runtime)
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# pool_pre_ping checks that a connection is alive before using it (avoids stale connections)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()  # base class that all ORM models extend


def get_db():
    """FastAPI dependency that yields a database session and closes it when done."""
    db = SessionLocal()
    try:
        yield db  # hand the session to the route handler
    finally:
        db.close()  # always close the session, even if an exception occurred
