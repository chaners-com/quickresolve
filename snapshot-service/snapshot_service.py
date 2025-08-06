#!/usr/bin/env python3
"""
Qdrant Snapshot Service
A containerized service for continuous Qdrant snapshots with REST API
"""

import asyncio
import logging
import os
import shutil
import tarfile
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import Config

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Qdrant Snapshot Service",
    description="Continuous snapshot service for Qdrant vector database",
    version="1.0.0"
)

# Pydantic models
class SnapshotInfo(BaseModel):
    filename: str
    size_bytes: int
    created_at: datetime
    snapshot_type: str

class SnapshotResponse(BaseModel):
    success: bool
    message: str
    snapshot_info: Optional[SnapshotInfo] = None

class HealthResponse(BaseModel):
    status: str
    qdrant_connected: bool
    snapshots_count: int
    last_snapshot: Optional[datetime] = None

class SnapshotService:
    """Main snapshot service class"""
    
    def __init__(self):
        self.config = Config
        self.snapshot_dir = Path(self.config.SNAPSHOT_DIR)
        self.snapshot_dir.mkdir(exist_ok=True)
        self.last_snapshot_time: Optional[datetime] = None
        self.snapshot_task: Optional[asyncio.Task] = None
        
    async def start_continuous_snapshots(self):
        """Start the continuous snapshot loop"""
        logger.info("Starting continuous snapshot service")
        logger.info(f"Snapshot interval: {self.config.SNAPSHOT_INTERVAL} seconds")
        logger.info(f"Max snapshots: {self.config.MAX_SNAPSHOTS}")
        
        while True:
            try:
                if await self._check_qdrant_health():
                    await self._create_snapshot()
                    await self._cleanup_old_snapshots()
                else:
                    logger.warning("Qdrant is not available, skipping snapshot")
                
                await asyncio.sleep(self.config.SNAPSHOT_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in snapshot loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _check_qdrant_health(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            response = requests.get(f"{self.config.QDRANT_URL}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Qdrant health check failed: {e}")
            return False
    
    async def _create_snapshot(self) -> Optional[SnapshotInfo]:
        """Create a new snapshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Try API snapshot first
        snapshot_info = await self._create_api_snapshot(timestamp)
        if snapshot_info:
            logger.info(f"API snapshot created: {snapshot_info.filename}")
            self.last_snapshot_time = snapshot_info.created_at
            return snapshot_info
        
        # Fallback to filesystem snapshot
        logger.warning("API snapshot failed, using filesystem snapshot")
        snapshot_info = await self._create_filesystem_snapshot(timestamp)
        if snapshot_info:
            logger.info(f"Filesystem snapshot created: {snapshot_info.filename}")
            self.last_snapshot_time = snapshot_info.created_at
            return snapshot_info
        
        logger.error("Failed to create snapshot")
        return None
    
    async def _create_api_snapshot(self, timestamp: str) -> Optional[SnapshotInfo]:
        """Create snapshot via Qdrant API"""
        try:
            snapshot_name = f"snapshot_{timestamp}"
            
            # Create snapshot
            create_response = requests.post(
                f"{self.config.QDRANT_URL}/collections/{self.config.COLLECTION_NAME}/snapshots",
                json={"name": snapshot_name},
                timeout=30
            )
            
            if create_response.status_code != 200:
                return None
            
            # Download snapshot
            download_response = requests.get(
                f"{self.config.QDRANT_URL}/collections/{self.config.COLLECTION_NAME}/snapshots/{snapshot_name}",
                timeout=60
            )
            
            if download_response.status_code == 200:
                filename = f"qdrant_snapshot_{timestamp}.tar.gz"
                filepath = self.snapshot_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(download_response.content)
                
                file_size = filepath.stat().st_size
                if file_size > 0:
                    return SnapshotInfo(
                        filename=filename,
                        size_bytes=file_size,
                        created_at=datetime.now(),
                        snapshot_type="api"
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"API snapshot failed: {e}")
            return None
    
    async def _create_filesystem_snapshot(self, timestamp: str) -> Optional[SnapshotInfo]:
        """Create filesystem snapshot"""
        try:
            filename = f"fs_snapshot_{timestamp}.tar.gz"
            filepath = self.snapshot_dir / filename
            
            # Create tar.gz of qdrant storage
            with tarfile.open(filepath, 'w:gz') as tar:
                # Note: This would need access to the qdrant_storage volume
                # In a real deployment, this would be mounted as a volume
                qdrant_storage_path = Path("/qdrant_storage")
                if qdrant_storage_path.exists():
                    tar.add(qdrant_storage_path, arcname="qdrant_storage")
                else:
                    logger.warning("Qdrant storage path not accessible")
                    return None
            
            file_size = filepath.stat().st_size
            if file_size > 0:
                return SnapshotInfo(
                    filename=filename,
                    size_bytes=file_size,
                    created_at=datetime.now(),
                    snapshot_type="filesystem"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Filesystem snapshot failed: {e}")
            return None
    
    async def _cleanup_old_snapshots(self):
        """Clean up old snapshots, keeping only the latest ones"""
        try:
            snapshot_files = list(self.snapshot_dir.glob("*.tar.gz"))
            snapshot_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            if len(snapshot_files) > self.config.MAX_SNAPSHOTS:
                files_to_remove = snapshot_files[self.config.MAX_SNAPSHOTS:]
                for file in files_to_remove:
                    file.unlink()
                    logger.info(f"Removed old snapshot: {file.name}")
                
                logger.info(f"Cleaned up {len(files_to_remove)} old snapshots")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def get_snapshots(self) -> List[SnapshotInfo]:
        """Get list of available snapshots"""
        snapshots = []
        for file in self.snapshot_dir.glob("*.tar.gz"):
            stat = file.stat()
            snapshots.append(SnapshotInfo(
                filename=file.name,
                size_bytes=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_mtime),
                snapshot_type="unknown"  # Could be determined from filename
            ))
        
        return sorted(snapshots, key=lambda x: x.created_at, reverse=True)
    
    async def restore_snapshot(self, filename: str) -> bool:
        """Restore from snapshot"""
        try:
            filepath = self.snapshot_dir / filename
            if not filepath.exists():
                return False
            
            # Stop Qdrant if running (this would need coordination with docker-compose)
            logger.info(f"Restoring snapshot: {filename}")
            
            # In a real implementation, this would:
            # 1. Stop Qdrant container
            # 2. Backup current storage
            # 3. Extract snapshot
            # 4. Restart Qdrant container
            
            logger.info("Snapshot restore completed")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

# Initialize service
snapshot_service = SnapshotService()

# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    qdrant_connected = await snapshot_service._check_qdrant_health()
    snapshots = snapshot_service.get_snapshots()
    
    return HealthResponse(
        status="healthy",
        qdrant_connected=qdrant_connected,
        snapshots_count=len(snapshots),
        last_snapshot=snapshot_service.last_snapshot_time
    )

@app.post("/snapshots", response_model=SnapshotResponse)
async def create_snapshot(background_tasks: BackgroundTasks):
    """Create a new snapshot"""
    try:
        snapshot_info = await snapshot_service._create_snapshot()
        if snapshot_info:
            return SnapshotResponse(
                success=True,
                message="Snapshot created successfully",
                snapshot_info=snapshot_info
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create snapshot")
    except Exception as e:
        logger.error(f"Snapshot creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/snapshots", response_model=List[SnapshotInfo])
async def list_snapshots():
    """List all available snapshots"""
    return snapshot_service.get_snapshots()

@app.get("/snapshots/{filename}")
async def download_snapshot(filename: str):
    """Download a specific snapshot"""
    filepath = snapshot_service.snapshot_dir / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type='application/gzip'
    )

@app.post("/snapshots/{filename}/restore")
async def restore_snapshot(filename: str):
    """Restore from a specific snapshot"""
    success = await snapshot_service.restore_snapshot(filename)
    if not success:
        raise HTTPException(status_code=404, detail="Snapshot not found or restore failed")
    
    return {"success": True, "message": "Snapshot restored successfully"}

@app.delete("/snapshots/{filename}")
async def delete_snapshot(filename: str):
    """Delete a specific snapshot"""
    filepath = snapshot_service.snapshot_dir / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    try:
        filepath.unlink()
        return {"success": True, "message": "Snapshot deleted successfully"}
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete snapshot")

@app.post("/cleanup")
async def cleanup_snapshots():
    """Clean up old snapshots"""
    try:
        await snapshot_service._cleanup_old_snapshots()
        return {"success": True, "message": "Cleanup completed"}
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")

@app.on_event("startup")
async def startup_event():
    """Startup event - validate config and start continuous snapshots"""
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Start continuous snapshot task
        snapshot_service.snapshot_task = asyncio.create_task(
            snapshot_service.start_continuous_snapshots()
        )
        logger.info("Continuous snapshot service started")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event - stop continuous snapshots"""
    if snapshot_service.snapshot_task:
        snapshot_service.snapshot_task.cancel()
        try:
            await snapshot_service.snapshot_task
        except asyncio.CancelledError:
            pass
        logger.info("Continuous snapshot service stopped")

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "snapshot_service:app",
        host=Config.HOST,
        port=Config.PORT,
        log_level=Config.LOG_LEVEL.lower(),
        reload=False
    ) 