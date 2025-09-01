#!/usr/bin/env python3
"""
Document Parsing Service
Parses PDF/DOC/DOCX to Markdown,
Once parsed, it forwards to the chunking service.
"""

import asyncio
import os
import time

import boto3
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.parsers.registry import PARSER_REGISTRY, get_parser_class

app = FastAPI(
    title="Document Parsing Service",
    description="""Parses PDF/DOC/DOCX to Markdown,
    uploads to S3, and forwards to the redaction service (then chunking).""",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment and clients
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
PUBLIC_S3_ENDPOINT = os.getenv("PUBLIC_S3_ENDPOINT")

TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://task-service:8010")

s3_client = None


@app.on_event("startup")
def on_startup():
    global s3_client
    s3_client = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )


class ParseRequest(BaseModel):
    s3_key: str
    file_id: str
    workspace_id: int
    original_filename: str
    task_id: str | None = None


class ParseAck(BaseModel):
    accepted: bool
    workspace_id: int
    file_id: str


async def _update_task_status(task_id: str, **kwargs):
    if not task_id:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.put(f"{TASK_SERVICE_URL}/task/{task_id}", json=kwargs)
    except Exception:
        pass


async def _download_from_s3(key: str) -> tuple[bytes, str]:
    def _get():
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        content_type = obj.get("ContentType") or ""
        return obj["Body"].read(), content_type

    return await asyncio.to_thread(_get)


async def _upload_to_s3(
    key: str, body: bytes, content_type: str = "text/markdown"
) -> None:
    def _put():
        s3_client.put_object(
            Bucket=S3_BUCKET, Key=key, Body=body, ContentType=content_type
        )

    await asyncio.to_thread(_put)


async def _notify_running(task_id: str | None, step: int, message: str):
    await _update_task_status(
        task_id,
        status_code=1,
        status={"message": message, "step": step},
    )


async def _run_parse_job(request: ParseRequest) -> None:
    started = time.time()
    try:
        print(
            f"""Parsing document {request.s3_key}
             for file {request.file_id} in workspace {request.workspace_id}"""
        )
        # Download original content (also capture content-type if set)
        content_bytes, s3_content_type = await _download_from_s3(
            request.s3_key
        )

        # Determine extension
        # TODO: do not only rely on the extension, also check the content type.
        ext = request.original_filename.lower().strip().split(".")[-1]

        # Select parser from registry by extension and content type,
        # honoring env overrides
        parser_cls = get_parser_class(
            ext, s3_content_type
        ) or PARSER_REGISTRY.get(ext)
        if not parser_cls:
            await _update_task_status(
                request.task_id,
                status_code=3,
                status={"message": "unsupported file type"},
            )
            print(f"Unsupported file type: .{ext}")
            return

        # Build context for parser
        parse_context = {
            "workspace_id": request.workspace_id,
            "file_id": request.file_id,
            "public_s3_endpoint": PUBLIC_S3_ENDPOINT,
        }

        # Parse using the parser class
        document_parser_version = getattr(parser_cls, "VERSION", "unknown")
        parser_result = parser_cls.parse(content_bytes, parse_context)
        if asyncio.iscoroutine(parser_result):
            parsed_md, images = await parser_result
        else:
            parsed_md, images = parser_result

        # Minimal validation
        if not parsed_md or len(parsed_md.strip()) < int(
            os.getenv("MIN_OUTPUT_CHARS", "20")
        ):
            await _update_task_status(
                request.task_id,
                status_code=3,
                status={"message": "validation failed"},
            )
            print(
                f"""Validation failed for file {request.file_id}:
                 insufficient output"""
            )
            return

        # Upload images (if any) to S3 under {workspace}/parsed/{file}/images
        image_base = f"{request.workspace_id}/parsed/{request.file_id}/images"
        for img in images or []:
            ext = (img.get("ext") or "png").lstrip(".")
            idx = img.get("index") or 0
            key = f"{image_base}/image-{idx}.{ext}"
            await _upload_to_s3(
                key, img.get("content", b""), content_type=f"image/{ext}"
            )

        parsed_bytes = parsed_md.encode("utf-8")
        parsed_s3_key = f"{request.workspace_id}/parsed/{request.file_id}.md"

        # Upload parsed markdown
        await _upload_to_s3(
            parsed_s3_key, parsed_bytes, content_type="text/markdown"
        )

        # Update task output; orchestrator will decide next step
        await _update_task_status(
            request.task_id,
            status_code=2,
            output={
                "parsed_s3_key": parsed_s3_key,
                "document_parser_version": document_parser_version,
                "images": [
                    {
                        "key": (
                            f"{request.workspace_id}/parsed/"
                            f"{request.file_id}/images/"
                            f"image-{(img.get('index') or 0)}."
                            f"{(img.get('ext') or 'png').lstrip('.')}"
                        )
                    }
                    for img in (images or [])
                ],
            },
        )

        duration = time.time() - started
        print(
            f"""Parse job completed
             for file {request.file_id} in {duration:.3f}s"""
        )
    except Exception as e:
        await _update_task_status(
            request.task_id,
            status_code=3,
            status={"message": f"Parse failed: {e}"},
        )
        print(f"Parse job failed for file {request.file_id}: {e}")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "document-parsing-service",
        "timestamp": int(time.time()),
    }


@app.get("/supported-types")
async def get_supported_types():
    return {
        "supported_formats": [
            {"extension": ".pdf", "description": "PDF documents"},
            {"extension": ".docx", "description": "Microsoft Word documents"},
            {
                "extension": ".doc",
                "description": "Microsoft Word legacy documents",
            },
        ]
    }


@app.post("/parse")
async def parse_document(request: ParseRequest):
    # Enqueue background parse job and return immediate ack
    asyncio.create_task(_run_parse_job(request))
    return ParseAck(
        accepted=True,
        workspace_id=request.workspace_id,
        file_id=request.file_id,
    )
