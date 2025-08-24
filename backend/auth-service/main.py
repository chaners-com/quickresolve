from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth_endpoints import auth_router
from shared.database import Base, engine
import os

# Create FastAPI app
app = FastAPI(
    title="QuickResolve Backend",
    description="Backend API for QuickResolve authentication and file management",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development
        "http://localhost:3001",  # Alternative Next.js port
        "http://localhost:8090",  # Landing page
        "https://your-frontend-domain.com",  # Production frontend TODO: update this
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    if engine:
        print("=== FORCING DATABASE SCHEMA UPDATE ===")
        
        # Force drop and recreate all tables (DEVELOPMENT ONLY!) TODO: To find an other solution
        # This will delete all existing data
        if os.getenv("FORCE_SCHEMA_UPDATE", "false").lower() == "true":
            print("Dropping all existing tables...")
            Base.metadata.drop_all(bind=engine)
            print("Creating tables with new schema...")
        
        # Create all tables with the correct schema
        Base.metadata.create_all(bind=engine)
        print("Database tables created/updated successfully")
        
        # Verify the schema
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Available tables: {tables}")
        
        if 'users' in tables:
            columns = [col['name'] for col in inspector.get_columns('users')]
            print(f"Users table columns: {columns}")

# Include authentication routes
app.include_router(auth_router)

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