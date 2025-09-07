import os
import time
from uuid import uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    Index,
    Integer,
    SmallInteger,
    String,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./task_service.db")

# Only create engine if DATABASE_URL is provided
if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_POOL_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "60")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        future=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None

Base = declarative_base()


def _now_seconds() -> int:
    return int(time.time())


class Task(Base):
    __tablename__ = "tasks"

    id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid4
    )
    creation_timestamp = Column(
        BigInteger, nullable=False, default=_now_seconds
    )
    modification_timestamp = Column(
        BigInteger, nullable=False, default=_now_seconds
    )
    name = Column(String, nullable=False)
    scheduled_start_timestamp = Column(
        BigInteger, nullable=False, default=_now_seconds
    )
    status_code = Column(SmallInteger, nullable=False, default=0)
    status = Column(JSON, nullable=False, default=dict)
    progress_percentage = Column(SmallInteger, nullable=False, default=0)
    input = Column(JSON, nullable=False, default=dict)
    state = Column(JSON, nullable=False, default=dict)
    output = Column(JSON, nullable=False, default=dict)
    start_timestamp = Column(BigInteger, nullable=True, default=None)
    end_timestamp = Column(BigInteger, nullable=True, default=None)
    workspace_id = Column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_tasks_status", "status_code"),
        Index(
            "idx_tasks_fifo",
            "name",
            "status_code",
            "scheduled_start_timestamp",
        ),
    )


class Consumer(Base):
    __tablename__ = "consumers"

    endpoint_url = Column(String, primary_key=True, nullable=False, index=True)
    health_url = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    is_ready = Column(SmallInteger, nullable=False, default=0)

    __table_args__ = (
        Index("idx_consumers_topic_ready", "topic", "is_ready"),
        Index("idx_consumers_endpoint", "endpoint_url"),
    )


# Helper used by main on startup


def wait_for_db_and_create_tables():
    if engine is None:
        raise RuntimeError("DATABASE_URL not configured")
    retries = 5
    while retries > 0:
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            break
        except OperationalError:
            time.sleep(5)
            retries -= 1
    if retries == 0:
        raise RuntimeError("Could not connect to the database")

    Base.metadata.create_all(bind=engine)
