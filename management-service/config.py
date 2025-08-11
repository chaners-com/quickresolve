import os
from typing import List


class Config:
    """Configuration for the management service"""

    # Service settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8004"))

    # Docker settings
    DOCKER_SOCKET: str = os.getenv("DOCKER_SOCKET", "/var/run/docker.sock")

    # Service dependencies (in shutdown order)
    SERVICES: List[str] = [
        "ai-agent-service",
        "embedding-service",
        "ingestion-service",
        "frontend",
        "snapshot-service",
        "qdrant",
        "minio",
        "db",
    ]

    # Graceful shutdown timeouts (in seconds)
    SHUTDOWN_TIMEOUTS = {
        "ai-agent-service": 30,
        "embedding-service": 30,
        "ingestion-service": 30,
        "frontend": 10,
        "snapshot-service": 30,
        "qdrant": 45,  # Extended timeout for data integrity
        "minio": 30,
        "db": 30,
    }

    # Health check settings
    HEALTH_CHECK_INTERVAL: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> None:
        """Validate configuration"""
        if not os.path.exists(cls.DOCKER_SOCKET):
            raise ValueError(f"Docker socket not found: {cls.DOCKER_SOCKET}")

        if cls.PORT < 1 or cls.PORT > 65535:
            raise ValueError("PORT must be between 1 and 65535")
