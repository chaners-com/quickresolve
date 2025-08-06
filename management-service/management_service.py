#!/usr/bin/env python3
"""
QuickResolve Management Service
Handles graceful shutdowns and service coordination
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import docker
import requests
from fastapi import FastAPI, HTTPException
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
    title="QuickResolve Management Service",
    description="Service management and graceful shutdown coordination",
    version="1.0.0"
)

# Pydantic models
class ServiceStatus(BaseModel):
    name: str
    status: str
    health: bool
    uptime: Optional[str] = None

class ShutdownResponse(BaseModel):
    success: bool
    message: str
    services_stopped: List[str]
    duration_seconds: float

class HealthResponse(BaseModel):
    status: str
    services: List[ServiceStatus]
    total_services: int
    healthy_services: int

class ManagementService:
    """Main management service class"""
    
    def __init__(self):
        self.config = Config
        self.docker_client = docker.from_env()
        self.shutdown_in_progress = False
        
    def get_service_status(self, service_name: str) -> ServiceStatus:
        """Get status of a specific service"""
        try:
            # Find container by service name pattern (Docker Compose naming)
            containers = self.docker_client.containers.list(
                filters={"label": f"com.docker.compose.service={service_name}"}
            )
            
            if not containers:
                # Try direct name lookup as fallback
                try:
                    container = self.docker_client.containers.get(service_name)
                    containers = [container]
                except:
                    pass
            
            if not containers:
                return ServiceStatus(
                    name=service_name,
                    status="not_found",
                    health=False
                )
            
            container = containers[0]  # Get the first matching container
            status = container.status
            health = container.attrs.get('State', {}).get('Health', {}).get('Status') == 'healthy'
            
            # Calculate uptime
            uptime = None
            if container.attrs.get('State', {}).get('StartedAt'):
                started_at = container.attrs['State']['StartedAt']
                if started_at != '0001-01-01T00:00:00Z':
                    try:
                        start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                        uptime_delta = datetime.now(start_time.tzinfo) - start_time
                        uptime = str(uptime_delta).split('.')[0]  # Remove microseconds
                    except:
                        pass
            
            return ServiceStatus(
                name=service_name,
                status=status,
                health=health,
                uptime=uptime
            )
        except Exception as e:
            logger.error(f"Error getting status for {service_name}: {e}")
            return ServiceStatus(
                name=service_name,
                status="unknown",
                health=False
            )
    
    def get_all_services_status(self) -> List[ServiceStatus]:
        """Get status of all services"""
        services = []
        for service_name in self.config.SERVICES:
            services.append(self.get_service_status(service_name))
        return services
    
    async def graceful_shutdown(self) -> ShutdownResponse:
        """Perform graceful shutdown of all services"""
        if self.shutdown_in_progress:
            raise HTTPException(status_code=409, detail="Shutdown already in progress")
        
        self.shutdown_in_progress = True
        start_time = time.time()
        stopped_services = []
        
        logger.info("Starting graceful shutdown sequence")
        
        try:
            # Stop services in reverse dependency order
            for service_name in self.config.SERVICES:
                try:
                    logger.info(f"Stopping {service_name}...")
                    
                    # Get timeout for this service
                    timeout = self.config.SHUTDOWN_TIMEOUTS.get(service_name, 30)
                    
                    # Find and stop the container with timeout
                    containers = self.docker_client.containers.list(
                        filters={"label": f"com.docker.compose.service={service_name}"}
                    )
                    
                    if not containers:
                        # Try direct name lookup as fallback
                        try:
                            container = self.docker_client.containers.get(service_name)
                            containers = [container]
                        except:
                            logger.warning(f"Container for {service_name} not found")
                            continue
                    
                    if containers:
                        container = containers[0]
                        container.stop(timeout=timeout)
                    else:
                        logger.warning(f"No container found for {service_name}")
                        continue
                    
                    stopped_services.append(service_name)
                    logger.info(f"Successfully stopped {service_name}")
                    
                    # Small delay between services
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error stopping {service_name}: {e}")
                    # Continue with other services
            
            duration = time.time() - start_time
            logger.info(f"Graceful shutdown completed in {duration:.2f} seconds")
            
            return ShutdownResponse(
                success=True,
                message="Graceful shutdown completed successfully",
                services_stopped=stopped_services,
                duration_seconds=duration
            )
            
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
            raise HTTPException(status_code=500, detail=f"Shutdown failed: {str(e)}")
        finally:
            self.shutdown_in_progress = False
    
    async def start_services(self, services: Optional[List[str]] = None) -> Dict[str, bool]:
        """Start specified services or all services"""
        if services is None:
            services = self.config.SERVICES
        
        results = {}
        
        for service_name in services:
            try:
                logger.info(f"Starting {service_name}...")
                
                # Find the container
                containers = self.docker_client.containers.list(
                    filters={"label": f"com.docker.compose.service={service_name}"}
                )
                
                if not containers:
                    # Try direct name lookup as fallback
                    try:
                        container = self.docker_client.containers.get(service_name)
                        containers = [container]
                    except:
                        logger.warning(f"Container for {service_name} not found")
                        results[service_name] = False
                        continue
                
                if containers:
                    container = containers[0]
                    container.start()
                    results[service_name] = True
                    logger.info(f"Successfully started {service_name}")
                else:
                    logger.warning(f"No container found for {service_name}")
                    results[service_name] = False
                
                # Small delay between services
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error starting {service_name}: {e}")
                results[service_name] = False
        
        return results
    
    async def restart_service(self, service_name: str) -> bool:
        """Restart a specific service"""
        try:
            logger.info(f"Restarting {service_name}...")
            
            # Find the container
            containers = self.docker_client.containers.list(
                filters={"label": f"com.docker.compose.service={service_name}"}
            )
            
            if not containers:
                # Try direct name lookup as fallback
                try:
                    container = self.docker_client.containers.get(service_name)
                    containers = [container]
                except:
                    logger.warning(f"Container for {service_name} not found")
                    return False
            
            if containers:
                container = containers[0]
                container.restart()
                logger.info(f"Successfully restarted {service_name}")
                return True
            else:
                logger.warning(f"No container found for {service_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error restarting {service_name}: {e}")
            return False
    
    def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy"""
        try:
            # Find the container
            containers = self.docker_client.containers.list(
                filters={"label": f"com.docker.compose.service={service_name}"}
            )
            
            if not containers:
                # Try direct name lookup as fallback
                try:
                    container = self.docker_client.containers.get(service_name)
                    containers = [container]
                except:
                    logger.warning(f"Container for {service_name} not found")
                    return False
            
            if containers:
                container = containers[0]
                health_status = container.attrs.get('State', {}).get('Health', {}).get('Status')
                return health_status == 'healthy'
            else:
                logger.warning(f"No container found for {service_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking health for {service_name}: {e}")
            return False

# Initialize service
management_service = ManagementService()

# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    services = management_service.get_all_services_status()
    healthy_count = sum(1 for s in services if s.health)
    
    return HealthResponse(
        status="healthy",
        services=services,
        total_services=len(services),
        healthy_services=healthy_count
    )

@app.get("/services", response_model=List[ServiceStatus])
async def get_services():
    """Get status of all services"""
    return management_service.get_all_services_status()

@app.get("/services/{service_name}", response_model=ServiceStatus)
async def get_service(service_name: str):
    """Get status of a specific service"""
    return management_service.get_service_status(service_name)

@app.post("/shutdown", response_model=ShutdownResponse)
async def shutdown_services():
    """Perform graceful shutdown of all services"""
    return await management_service.graceful_shutdown()

@app.post("/services/start")
async def start_services(services: Optional[List[str]] = None):
    """Start services"""
    results = await management_service.start_services(services)
    return {
        "success": True,
        "message": "Services started",
        "results": results
    }

@app.post("/services/{service_name}/restart")
async def restart_service(service_name: str):
    """Restart a specific service"""
    success = await management_service.restart_service(service_name)
    if success:
        return {"success": True, "message": f"Service {service_name} restarted successfully"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to restart {service_name}")

@app.get("/services/{service_name}/health")
async def check_service_health(service_name: str):
    """Check health of a specific service"""
    is_healthy = management_service.check_service_health(service_name)
    return {
        "service": service_name,
        "healthy": is_healthy,
        "timestamp": datetime.now().isoformat()
    }

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    asyncio.create_task(management_service.graceful_shutdown())

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

@app.on_event("startup")
async def startup_event():
    """Startup event - validate configuration"""
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
        logger.info("Management service started")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    logger.info("Management service shutting down")

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "management_service:app",
        host=Config.HOST,
        port=Config.PORT,
        log_level=Config.LOG_LEVEL.lower(),
        reload=False
    ) 