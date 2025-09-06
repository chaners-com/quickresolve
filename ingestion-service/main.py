import asyncio
import os
import tempfile
import time
from typing import Optional
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
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text  # Import text function
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


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


app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8090",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Location", "Content-Location", "location"],
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

# Upload size limit (bytes)
try:
    _mb = os.getenv("MAX_UPLOAD_MB", "4")
    MAX_UPLOAD_BYTES = 0
    if _mb is not None and str(_mb).strip() != "":
        MAX_UPLOAD_BYTES = int(float(_mb) * 1024 * 1024)
    else:
        MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "0") or "0")
except ValueError:
    MAX_UPLOAD_BYTES = 0


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


async def _bg_upload_and_trigger(
    tmp_path: str, s3_bucket: str, s3_key: str, db_file_id: UUID
) -> None:
    try:
        # Upload from temp file path
        await asyncio.to_thread(s3.upload_file, tmp_path, s3_bucket, s3_key)
        # Cleanup temp file
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        # Persist s3_key
        try:
            db2 = SessionLocal()
            rec = db2.query(DBFile).filter(DBFile.id == db_file_id).first()
            if rec:
                rec.s3_key = s3_key
                db2.commit()
        finally:
            db2.close()
    except Exception as e:
        try:
            db2 = SessionLocal()
            rec = db2.query(DBFile).filter(DBFile.id == db_file_id).first()
            if rec:
                print(f"Failed to upload to S3: {e}")
                print(f"Marking file {db_file_id} as failed")
                rec.status = 3
                db2.commit()
        finally:
            db2.close()
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@app.post("/uploadfile", status_code=202)
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
        # Copy stream to disk off the event loop with size limit
        await asyncio.to_thread(
            _copy_stream_to_path,
            file.file,
            tmp_path,
            MAX_UPLOAD_BYTES,
        )
    except HTTPException:
        # Propagate 413 directly
        try:
            db_file.status = 3
            db.commit()
            db.refresh(db_file)
        except Exception:
            pass
        raise
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
    asyncio.create_task(
        _bg_upload_and_trigger(tmp_path, S3_BUCKET, s3_key, db_file.id)
    )

    # 4) Create index-document task now and return 202 with Location header
    try:
        task_service_url = os.getenv(
            "TASK_SERVICE_URL", "http://task-service:8010"
        )
        is_md = (file.filename or "").lower().endswith(".md")
        steps = []
        if not is_md:
            steps.append({"name": "parse-document"})
        steps.extend(
            [
                {"name": "chunk"},
                {"name": "redact"},
                {"name": "embed"},
            ]
        )
        index_definition = {
            "description": f"Indexing document {db_file.id}",
            "s3_key": s3_key,
            "file_id": str(db_file.id),
            "workspace_id": workspace_id,
            "original_filename": file.filename or "",
            "steps": steps,
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{task_service_url}/task",
                json={
                    "name": "index-document",
                    "input": index_definition,
                    "workspace_id": workspace_id,
                },
            )
            r.raise_for_status()
            task_id = r.json().get("id")
            if not task_id:
                raise HTTPException(
                    status_code=500, detail="Task creation did not return id"
                )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create index task: {e}"
        )

    status_url = f"http://localhost:8010/task/{task_id}/status"
    return Response(status_code=202, headers={"Location": status_url})


def _copy_stream_to_path(
    src_fileobj, dst_path: str, max_bytes: Optional[int] = None
) -> None:
    src_fileobj.seek(0)
    total = 0
    with open(dst_path, "wb") as out_f:
        while True:
            chunk = src_fileobj.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if max_bytes and max_bytes > 0 and total > max_bytes:
                # Stop writing and signal too large
                raise HTTPException(status_code=413, detail="File too large")
            out_f.write(chunk)


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
