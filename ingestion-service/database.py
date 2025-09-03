import os
import time
from contextlib import contextmanager

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    create_engine,
    text,
)
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# Only create engine if DATABASE_URL is provided
if DATABASE_URL:
    # Use the improved pooling configuration from remote (already optimized)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_POOL_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "60")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        future=True,
    )
    
    # Create session factory with retry logic (your enhancement)
    SessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=engine,
        expire_on_commit=False  # Prevent expired object access issues
    )
else:
    engine = None
    SessionLocal = None

Base = declarative_base()


def get_db_with_retry(max_retries=3, retry_delay=1):
    """
    Get database session with retry logic for connection failures.
    """
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Test the connection with a simple query
            db.execute(text("SELECT 1"))
            return db
        except (OperationalError, DisconnectionError) as e:
            db.close() if 'db' in locals() else None
            if attempt == max_retries - 1:
                raise e
            print(f"Database connection failed, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff


@contextmanager
def get_db_session():
    """
    Context manager for database sessions with automatic cleanup and retry logic.
    """
    db = None
    try:
        db = get_db_with_retry()
        yield db
    except Exception as e:
        if db:
            db.rollback()
        raise e
    finally:
        if db:
            db.close()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    workspaces = relationship("Workspace", back_populates="owner")


class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="workspaces")
    files = relationship("File", back_populates="workspace")


class File(Base):
    __tablename__ = "files"
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    name = Column(String, index=True)
    s3_key = Column(String, unique=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    workspace = relationship("Workspace", back_populates="files")
    status = Column(SmallInteger, nullable=False, default=1)
