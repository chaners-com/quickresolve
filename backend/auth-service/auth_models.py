import os
from datetime import datetime
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    DateTime,
    Boolean,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

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

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    company_name = Column(String, nullable=True)          
    team_size = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workspaces = relationship("Workspace", back_populates="owner")

class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="workspaces")
    files = relationship("File", back_populates="workspace")

class File(Base):
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    name = Column(String, index=True)
    s3_key = Column(String, unique=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    status = Column(SmallInteger, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="files")

# Database dependency
def get_db():
    if SessionLocal is None:
        raise Exception("Database not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
def create_tables():
    if engine:
        Base.metadata.create_all(bind=engine)