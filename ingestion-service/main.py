import os
import time

import boto3
import requests
from database import Base
from database import File as DBFile
from database import SessionLocal, User, Workspace, engine
from fastapi import Depends, FastAPI, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text  # Import text function
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# --- Improved Pydantic Models ---


class UserCreate(BaseModel):
    username: str


class UserResponse(UserCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(BaseModel):
    name: str
    owner_id: int


class WorkspaceResponse(WorkspaceCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class FileStatusResponse(BaseModel):
    file_id: int
    status: int


app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Global variables for S3
S3_ENDPOINT = None
S3_ACCESS_KEY = None
S3_SECRET_KEY = None
S3_BUCKET = None
s3 = None


@app.on_event("startup")
def on_startup():
    global s3, S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET

    # Initialize S3 configuration
    S3_ENDPOINT = os.getenv("S3_ENDPOINT")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
    S3_BUCKET = os.getenv("S3_BUCKET")

    # Validate S3 configuration
    if not all([S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET]):
        print("Error: Missing S3 configuration environment variables")
        exit(1)

    # Initialize S3 client
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )

    # Wait for the database to be ready
    retries = 5
    while retries > 0:
        try:
            # Try to connect to the database
            db = SessionLocal()
            db.execute(text("SELECT 1"))  # Use text() function
            db.close()
            print("Database is ready.")
            break
        except OperationalError:
            print("Database not ready, waiting...")
            time.sleep(5)
            retries -= 1

    if retries == 0:
        print("Could not connect to the database. Exiting.")
        exit(1)

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Ensure S3 bucket exists
    try:
        s3.head_bucket(Bucket=S3_BUCKET)
        print(f"S3 bucket '{S3_BUCKET}' is ready.")
    except Exception:
        print(f"Creating S3 bucket '{S3_BUCKET}'...")
        s3.create_bucket(Bucket=S3_BUCKET)
        print(f"S3 bucket '{S3_BUCKET}' created successfully.")


@app.post("/uploadfile/")
async def create_upload_file(
    file: UploadFile, workspace_id: int, db: Session = Depends(get_db)
):
    workspace = (
        db.query(Workspace).filter(Workspace.id == workspace_id).first()
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    s3_key = f"{workspace.id}/{file.filename}"

    # Overwrite the file in S3
    try:
        s3.upload_fileobj(file.file, S3_BUCKET, s3_key)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload to S3: {e}"
        )

    # Check if the file record already exists
    db_file = db.query(DBFile).filter(DBFile.s3_key == s3_key).first()

    if not db_file:
        # Create a new file record if it doesn't exist
        db_file = DBFile(
            name=file.filename, s3_key=s3_key, workspace_id=workspace_id, status=1
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)

    # Trigger the embedding service (for both new and existing files)
    embedding_service_url = "http://embedding-service:8001/embed/"
    try:
        requests.post(
            embedding_service_url,
            json={
                "s3_key": s3_key,
                "file_id": db_file.id,
                "workspace_id": workspace_id,
            },
            timeout=30,  # Add timeout to prevent hanging requests
        )
    except requests.exceptions.RequestException:
        # In a real app, you might want a retry mechanism or a more robust way
        # to handle the embedding service being temporarily unavailable.
        print("Failed to trigger embedding service")

    return {"filename": file.filename, "s3_key": s3_key, "id": db_file.id, "status": db_file.status}


@app.get("/file-content/")
def get_file_content(s3_key: str):
    """
    Retrieves the content of a file from S3 given its key.
    """
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        file_content = response["Body"].read().decode("utf-8")
        return {"content": file_content}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve file from S3: {e}"
        )


# --- User and Workspace Endpoints ---


@app.post("/users/", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = (
        db.query(User).filter(User.username == user.username).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=409,  # Conflict
            detail=(
                "Username already registered. Please choose a different one."
            ),
        )

    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users/", response_model=list[UserResponse])
def get_user_by_name(username: str, db: Session = Depends(get_db)):
    """
    Looks up a user by their exact username.
    Returns a list containing the user if found, otherwise an empty list.
    """
    user = db.query(User).filter(User.username == username).first()
    return [user] if user else []


@app.post("/workspaces/", response_model=WorkspaceResponse, status_code=201)
def create_workspace(
    workspace: WorkspaceCreate, db: Session = Depends(get_db)
):
    owner = db.query(User).filter(User.id == workspace.owner_id).first()
    if not owner:
        raise HTTPException(
            status_code=404,
            detail=f"User with id {workspace.owner_id} not found",
        )

    db_workspace = Workspace(**workspace.model_dump())
    db.add(db_workspace)
    db.commit()
    db.refresh(db_workspace)
    return db_workspace


@app.get("/workspaces/", response_model=list[WorkspaceResponse])
def get_workspace_by_name(
    name: str, owner_id: int, db: Session = Depends(get_db)
):
    """
    Looks up a workspace by its exact name for a specific owner.
    Returns a list containing the workspace if found, otherwise an empty list.
    """
    workspace = (
        db.query(Workspace)
        .filter(Workspace.name == name, Workspace.owner_id == owner_id)
        .first()
    )
    return [workspace] if workspace else []


# --- File Status Endpoints ---


@app.get("/files/{file_id}/status", response_model=FileStatusResponse)
def get_file_status(file_id: int, db: Session = Depends(get_db)):
    file = db.query(DBFile).filter(DBFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return FileStatusResponse(file_id=file.id, status=file.status)


@app.put("/files/{file_id}/status", response_model=FileStatusResponse)
def update_file_status(
    file_id: int,
    status: int = Query(..., ge=1, le=2),
    db: Session = Depends(get_db)
):
    file = db.query(DBFile).filter(DBFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    file.status = status
    db.commit()
    db.refresh(file)
    return FileStatusResponse(file_id=file.id, status=file.status)
