from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth_endpoints import auth_router, users_router, files_router
import sys
sys.path.insert(0, '/app/backend')
from backend.db.database import init_database
import os

# Create FastAPI app
app = FastAPI(
    title="QuickResolve Backend",
    description="Backend API for QuickResolve authentication and file management",
    version="1.0.0"
)

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")

# Add CORS middleware with secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods only
    allow_headers=[
        "Authorization",
        "Content-Type", 
        "X-CSRF-Token",
        "X-Requested-With",
        "Accept"
    ],  # Specific headers only
    expose_headers=["X-CSRF-Token"],  # Headers that frontend can access
)

@app.on_event("startup")
async def startup_event():
    """Initialize database - this is the single source of truth for database creation"""
    init_database()

# Include all routes
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(files_router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "QuickResolve Backend API",
        "version": "1.0.0",
        "status": "running"
    }

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Backend service is running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)