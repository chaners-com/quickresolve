"""
Database configuration and initialization - Single file with all models and functions
"""
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

# Create database engine and session factory
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

Base = declarative_base()

# Database Models
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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """
    Initialize the database with all required tables.
    This function should only be called from the auth service.
    """
    print("=== INITIALIZING DATABASE FROM AUTH SERVICE ===")
    
    # Retry logic for database connection
    import time
    max_retries = 30
    retry_interval = 2
    
    for attempt in range(max_retries):
        try:
            print(f"Database connection attempt {attempt + 1}/{max_retries}")
            
            # Test the connection first
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("Database connection successful")
            
            # Safe table creation - only create if they don't exist
            Base.metadata.create_all(bind=engine, checkfirst=True)
            print("Database tables created/verified successfully")
            
            # Verify the schema
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"Available tables: {tables}")
            
            if 'users' in tables:
                columns = [col['name'] for col in inspector.get_columns('users')]
                print(f"Users table columns: {columns}")
            
            if 'workspaces' in tables:
                columns = [col['name'] for col in inspector.get_columns('workspaces')]
                print(f"Workspaces table columns: {columns}")
                
            if 'files' in tables:
                columns = [col['name'] for col in inspector.get_columns('files')]
                print(f"Files table columns: {columns}")
            
            print("Database initialization completed successfully from auth service")
            break
            
        except Exception as e:
            print(f"Database connection attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                print("Max retries exceeded. Database initialization failed.")
                raise RuntimeError(f"Failed to initialize database after {max_retries} attempts: {e}")
    
    # Add migration reminder
    print("Note: For production deployments, use proper database migrations instead of auto-creation")
    print("=== DATABASE INITIALIZATION COMPLETE ===")

def create_tables():
    """
    Create database tables. For backward compatibility with services that expect this function.
    """
    print("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("Database tables created/updated successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")
        print("Continuing with existing database schema...")

# Make sure all imports are available for other services
__all__ = ['Base', 'User', 'Workspace', 'File', 'get_db', 'engine', 'SessionLocal', 'init_database', 'create_tables']