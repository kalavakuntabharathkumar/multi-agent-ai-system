# SQLAlchemy ORM model for the jobs table.
# A Job row tracks the lifecycle of a long-running task submitted to the background queue.

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # auto-generated UUID primary key
    input_text = Column(Text, nullable=False)                               # the raw task text submitted by the user
    status = Column(String(20), nullable=False, default="queued")           # lifecycle state: queued → processing → done/failed
    result = Column(Text, nullable=True)                                     # JSON-serialized result, populated when done
    created_at = Column(DateTime, default=datetime.utcnow)                  # timestamp when the job was created
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # auto-updated on every change
