from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID
from backend.db.database import get_db,create_tables
from auth_service import (
    AuthService,
    UserLogin,
    UserRegister,
    LoginResponse,
    UserResponse,
)

from auth_models import User, Workspace, File


# ---------------------------------------
# Routers
# ---------------------------------------
auth_router = APIRouter(prefix="/auth", tags=["authentication"]) 
users_router = APIRouter(prefix="/users", tags=["users"])
files_router = APIRouter(prefix="/files", tags=["files"])

# Optionally initialize DB tables (prefer migrations in production) TODO: check this after
create_tables

# ---------------------------------------
# Helpers / Dependencies
# ---------------------------------------

def get_current_user_dep(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Extract current user from Authorization: Bearer <token>."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    try:
        token = authorization.replace("Bearer ", "")
        user = AuthService.get_current_user(db, token)
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

# ---------------------------------------
# Pydantic schemas for new endpoints
# ---------------------------------------
from pydantic import BaseModel, Field

class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    team_size: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

class WorkspaceOut(BaseModel):
    id: int
    name: str
    created_at: datetime

class FileOut(BaseModel):
    id: str
    name: str
    s3_key: Optional[str] = None
    workspace_id: int
    status: Optional[str] = None
    created_at: datetime
    workspace: Optional[WorkspaceOut] = None

class FileStatusOut(BaseModel):
    id: str
    name: str
    status: Optional[str] = None
    created_at: datetime

# ---------------------------------------
# AUTH ENDPOINTS
# ---------------------------------------

@auth_router.post("/login", response_model=LoginResponse)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token"""
    try:
        return AuthService.login_user(db, login_data)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login",
        )

@auth_router.post("/register", response_model=LoginResponse)
async def register(
    register_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Register new user and return JWT token"""
    try:
        return AuthService.register_user(db, register_data)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration",
        )

@auth_router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_user_dep),
):
    """Get current authenticated user"""
    # Convert ORM user to the existing pydantic response model
    return UserResponse.model_validate(current_user)

@auth_router.post("/logout")
async def logout():
    """Logout user (client-side token removal)"""
    return {"message": "Logout successful"}

@auth_router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user_dep),
):
    """Refresh JWT token"""
    try:
        token_data = {
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
        }
        new_token = AuthService.create_jwt_token(token_data)
        return {"token": new_token, "message": "Token refreshed successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

@auth_router.get("/health")
async def auth_health_check():
    """Health check for authentication service"""
    return {"status": "healthy", "service": "authentication", "message": "Auth service is running"}

# ---------------------------------------
# USERS ENDPOINTS
# ---------------------------------------
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@users_router.put("/{user_id}", response_model=UserResponse)
async def update_user_profile(
    user_id: int,
    user_update: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    """Update user profile information (self only)."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Uniqueness checks
    if user_update.email and user_update.email != user.email:
        exists = db.query(User).filter(User.email == user_update.email).first()
        if exists:
            raise HTTPException(status_code=400, detail="Email already registered")

    if user_update.username and user_update.username != user.username:
        exists = db.query(User).filter(User.username == user_update.username).first()
        if exists:
            raise HTTPException(status_code=400, detail="Username already taken")

    # Apply updates
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)

    user.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(user)
        return UserResponse.model_validate(user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user profile")

@users_router.put("/{user_id}/change-password")
async def change_user_password(
    user_id: int,
    password_change: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    """Change user password (self only)."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    if not pwd_context.verify(password_change.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate and hash new password
    new_hash = pwd_context.hash(password_change.new_password)
    user.password_hash = new_hash
    user.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        return {"message": "Password changed successfully"}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to change password")

# ---------------------------------------
# FILES ENDPOINTS
# ---------------------------------------

@files_router.get("/", response_model=List[FileOut])
async def get_user_files(
    user_id: int,
    workspace_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    """Get files for a user (self only), optionally filtered by workspace."""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Get user's workspaces
    user_workspaces = db.query(Workspace).filter(Workspace.owner_id == user_id).all()
    workspace_ids = [ws.id for ws in user_workspaces]

    if not workspace_ids:
        return []

    # Base query
    query = db.query(File).filter(File.workspace_id.in_(workspace_ids))

    # Optional filter
    if workspace_id:
        if workspace_id not in workspace_ids:
            raise HTTPException(status_code=404, detail="Workspace not found")
        query = query.filter(File.workspace_id == workspace_id)

    files = query.order_by(File.created_at.desc()).limit(limit).all()

    # Build response
    ws_map = {ws.id: ws for ws in user_workspaces}
    result: List[FileOut] = []
    for f in files:
        ws = ws_map.get(f.workspace_id)
        result.append(
            FileOut(
                id=str(f.id),
                name=f.name,
                s3_key=getattr(f, "s3_key", None),
                workspace_id=f.workspace_id,
                status=getattr(f, "status", None),
                created_at=f.created_at,
                workspace=(
                    WorkspaceOut(id=ws.id, name=ws.name, created_at=ws.created_at) if ws else None
                ),
            )
        )

    return result

@files_router.get("/{file_id}/status", response_model=FileStatusOut)
async def get_file_status(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dep),
):
    """Get the processing status of a specific file owned by the current user."""
    # Parse UUID
    try:
        file_uuid = UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file ID format")

    # Load file
    file = db.query(File).filter(File.id == file_uuid).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Ownership check via workspace owner
    ws = db.query(Workspace).filter(Workspace.id == file.workspace_id).first()
    if not ws or ws.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return FileStatusOut(
        id=str(file.id), name=file.name, status=getattr(file, "status", None), created_at=file.created_at
    )

