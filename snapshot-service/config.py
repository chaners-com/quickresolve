import os
from typing import Optional

class Config:
    """Configuration for the snapshot service"""
    
    # Snapshot settings
    SNAPSHOT_INTERVAL: int = int(os.getenv("SNAPSHOT_INTERVAL", "300"))  # 5 minutes
    MAX_SNAPSHOTS: int = int(os.getenv("MAX_SNAPSHOTS", "10"))
    SNAPSHOT_DIR: str = os.getenv("SNAPSHOT_DIR", "/app/snapshots")
    
    # Qdrant settings
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://qdrant:6333")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "file_embeddings")
    
    # Service settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8003"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Health check settings
    HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
    
    @classmethod
    def validate(cls) -> None:
        """Validate configuration"""
        if cls.SNAPSHOT_INTERVAL < 60:
            raise ValueError("SNAPSHOT_INTERVAL must be at least 60 seconds")
        
        if cls.MAX_SNAPSHOTS < 1:
            raise ValueError("MAX_SNAPSHOTS must be at least 1")
        
        if not cls.QDRANT_URL:
            raise ValueError("QDRANT_URL is required")
        
        if not cls.COLLECTION_NAME:
            raise ValueError("COLLECTION_NAME is required") 