import asyncio
import os
import shutil
import tempfile
import time
from uuid import UUID

import boto3
import httpx
from database import Base
from database import File as DBFile
from database import SessionLocal, User, Workspace, engine
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
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
    file_id: UUID
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
    expose_headers=["Location"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ingestion-service"}


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


async def _trigger_downstream(
    md: bool, s3_key: str, db_file_id: str, workspace_id: int, filename: str
):
    try:
        if md:
            redaction_service_url = os.getenv(
                "REDACTION_SERVICE_URL", "http://redaction-service:8007"
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{redaction_service_url}/redact",
                    json={
                        "s3_key": s3_key,
                        "file_id": db_file_id,
                        "workspace_id": workspace_id,
                        "original_filename": filename,
                    },
                )
        else:
            parsing_service_url = os.getenv(
                "PARSING_SERVICE_URL", "http://document-parsing-service:8005"
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{parsing_service_url}/parse/",
                    json={
                        "s3_key": s3_key,
                        "file_id": db_file_id,
                        "workspace_id": workspace_id,
                        "original_filename": filename,
                    },
                )
    except Exception:
        # best-effort fire-and-forget
        pass


@app.post("/uploadfile/", status_code=202)
async def create_upload_file(
    file: UploadFile,
    workspace_id: int,
    db: Session = Depends(get_db),
    response: Response = None,
):
    workspace = (
        db.query(Workspace).filter(Workspace.id == workspace_id).first()
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # 1) Create DB record first to get UUID id
    db_file = DBFile(
        name=file.filename,
        workspace_id=workspace_id,
        status=1,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    # 2) Build S3 key using uuid + original extension
    _, ext = os.path.splitext(file.filename)
    ext = (ext or "").lower()
    s3_key = f"{workspace.id}/{db_file.id}{ext}"

    # Persist incoming upload to a temporary file before returning,
    # so background task can read it
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp_path = tmp.name
        tmp.close()
        # Copy stream to disk off the event loop
        await asyncio.to_thread(
            _copy_stream_to_path,
            file.file,
            tmp_path,
        )
    except Exception as e:
        # Mark error and fail fast
        try:
            db_file.status = 3
            db.commit()
            db.refresh(db_file)
        except Exception:
            pass
        raise HTTPException(
            status_code=500, detail=f"Failed to buffer upload: {e}"
        )

    # 3) Upload the file to S3 in background to avoid blocking connection
    async def _bg_upload_and_trigger():
        try:
            # Upload from temp file path
            await asyncio.to_thread(
                s3.upload_file, tmp_path, S3_BUCKET, s3_key
            )
            # Cleanup temp file
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            # Persist s3_key
            try:
                db2 = SessionLocal()
                rec = db2.query(DBFile).filter(DBFile.id == db_file.id).first()
                if rec:
                    rec.s3_key = s3_key
                    db2.commit()
            finally:
                db2.close()
            # Route by file type
            is_md = (file.filename or "").lower().endswith(".md")
            await _trigger_downstream(
                is_md,
                s3_key,
                str(db_file.id),
                workspace_id,
                file.filename or "",
            )
        except Exception as e:
            try:
                db2 = SessionLocal()
                rec = db2.query(DBFile).filter(DBFile.id == db_file.id).first()
                if rec:
                    print(f"Failed to upload to S3: {e}")
                    print(f"Marking file {db_file.id} as failed")
                    rec.status = 3
                    db2.commit()
            finally:
                db2.close()
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    asyncio.create_task(_bg_upload_and_trigger())

    # 4) Set Location header to status endpoint and return immediately
    if response is not None:
        response.headers["Location"] = (
            f"http://localhost:8000/files/{db_file.id}/status"
        )

    return {
        "filename": file.filename,
        "s3_key": s3_key,
        "id": db_file.id,
        "status": db_file.status,
    }


def _copy_stream_to_path(src_fileobj, dst_path: str) -> None:
    src_fileobj.seek(0)
    with open(dst_path, "wb") as out_f:
        shutil.copyfileobj(src_fileobj, out_f, length=1024 * 1024)


@app.get("/file-content/")
async def get_file_content(s3_key: str):
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
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
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
async def get_user_by_name(username: str, db: Session = Depends(get_db)):
    """
    Looks up a user by their exact username.
    Returns a list containing the user if found, otherwise an empty list.
    """
    user = db.query(User).filter(User.username == username).first()
    return [user] if user else []


@app.post("/workspaces/", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
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
async def get_workspace_by_name(
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


@app.get("/workspaces/all", response_model=list[WorkspaceResponse])
async def get_all_workspaces(db: Session = Depends(get_db)):
    """
    Get all available workspaces.
    Returns a list of all workspaces in the system.
    """
    workspaces = db.query(Workspace).all()
    return workspaces


# --- File Status Endpoints ---


@app.get("/files/{file_id}/status", response_model=FileStatusResponse)
async def get_file_status(file_id: UUID, db: Session = Depends(get_db)):
    file = db.query(DBFile).filter(DBFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return FileStatusResponse(file_id=file.id, status=file.status)


@app.put("/files/{file_id}/status", response_model=FileStatusResponse)
async def update_file_status(
    file_id: UUID,
    status: int = Query(..., ge=1, le=3),
    db: Session = Depends(get_db),
):
    file = db.query(DBFile).filter(DBFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    file.status = status
    db.commit()
    db.refresh(file)
    return FileStatusResponse(file_id=file.id, status=file.status)
