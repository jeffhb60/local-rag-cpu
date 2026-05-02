import shutil
from pathlib import Path
from threading import Thread
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder

from api.schemas import (
    AvailableDocument,
    DocumentsResponse,
    IngestResponse,
    JobStartResponse,
    ReindexResponse,
)
from config import settings
from core.document_loader import DocumentLoader
from core.ingestion import IngestionPipeline
from core.progress import jobs
from core.state import IndexState
from core.vectorstore import VectorStore


router = APIRouter(tags=["documents"])


def safe_filename(filename: str) -> str:
    """
    Prevent path traversal from uploaded filenames.

    Example:
    ../../evil.pdf -> evil.pdf
    """
    return Path(filename).name


def validate_upload_filename(filename: str) -> str:
    """
    Validate and sanitize an uploaded filename before saving it.

    This prevents:
    - path traversal
    - blank filenames
    - unsupported file types

    Client-side file restrictions can be bypassed, so the API must validate.
    """
    clean_name = safe_filename(filename)

    if not clean_name:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    extension = Path(clean_name).suffix.lower()

    if extension not in DocumentLoader.SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(DocumentLoader.SUPPORTED_EXTENSIONS))

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {extension or '[none]'}. "
                f"Allowed types: {allowed}."
            ),
        )

    return clean_name


def resolve_upload_destination(filename: str, force_rebuild: bool) -> Path:
    """
    Resolve the upload destination and prevent accidental overwrites.

    Policy:
    - If the file does not exist, allow save.
    - If the file exists and force_rebuild=True, overwrite intentionally.
    - If the file exists and force_rebuild=False, reject with 409 Conflict.
    """
    destination = settings.docs_dir / filename

    if destination.exists() and not force_rebuild:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A document named '{filename}' already exists. "
                "Enable Force rebuild to overwrite and reindex it."
            ),
        )

    return destination


def serialize_model(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()

    if isinstance(model, dict):
        return model

    return jsonable_encoder(model)


def run_upload_job(
    job_id: str,
    saved_paths: list[Path],
    force_rebuild: bool,
) -> None:
    try:
        jobs.update(
            job_id,
            status="running",
            current=0,
            total=len(saved_paths),
            message=f"Starting upload indexing for {len(saved_paths)} file(s).",
        )

        pipeline = IngestionPipeline(settings)

        details: list[IngestResponse] = []
        indexed = 0
        skipped = 0
        total_chunks = 0

        for file_index, path in enumerate(saved_paths, start=1):
            jobs.update(
                job_id,
                current=file_index - 1,
                message=f"Indexing uploaded file {file_index}/{len(saved_paths)}: {path.name}",
            )

            def progress(message: str) -> None:
                jobs.update(
                    job_id,
                    current=file_index - 1,
                    message=message,
                )

            result = pipeline.ingest_file(
                path=path,
                force_rebuild=force_rebuild,
                progress_callback=progress,
            )

            details.append(result)

            if result.status == "indexed":
                indexed += 1
                total_chunks += result.chunks_added
            elif result.status == "skipped":
                skipped += 1

            jobs.update(
                job_id,
                current=file_index,
                message=f"Finished {path.name}.",
            )

        response = ReindexResponse(
            status="complete",
            files_seen=len(saved_paths),
            files_indexed=indexed,
            files_skipped=skipped,
            chunks_added=total_chunks,
            details=details,
        )

        jobs.succeed(job_id, serialize_model(response))

    except Exception as exc:
        jobs.fail(job_id, str(exc))


def run_reindex_job(
    job_id: str,
    paths: list[Path],
    force_rebuild: bool,
) -> None:
    try:
        jobs.update(
            job_id,
            status="running",
            current=0,
            total=len(paths),
            message=f"Starting reindex for {len(paths)} file(s).",
        )

        pipeline = IngestionPipeline(settings)

        details: list[IngestResponse] = []
        indexed = 0
        skipped = 0
        total_chunks = 0

        for file_index, path in enumerate(paths, start=1):
            jobs.update(
                job_id,
                current=file_index - 1,
                message=f"Reindexing file {file_index}/{len(paths)}: {path.name}",
            )

            def progress(message: str) -> None:
                jobs.update(
                    job_id,
                    current=file_index - 1,
                    message=message,
                )

            result = pipeline.ingest_file(
                path=path,
                force_rebuild=force_rebuild,
                progress_callback=progress,
            )

            details.append(result)

            if result.status == "indexed":
                indexed += 1
                total_chunks += result.chunks_added
            elif result.status == "skipped":
                skipped += 1

            jobs.update(
                job_id,
                current=file_index,
                message=f"Finished {path.name}.",
            )

        response = ReindexResponse(
            status="complete",
            files_seen=len(paths),
            files_indexed=indexed,
            files_skipped=skipped,
            chunks_added=total_chunks,
            details=details,
        )

        jobs.succeed(job_id, serialize_model(response))

    except Exception as exc:
        jobs.fail(job_id, str(exc))


@router.get("/documents", response_model=DocumentsResponse)
async def list_documents():
    pipeline = IngestionPipeline(settings)
    state = IndexState(settings)
    vectorstore = VectorStore(settings)

    files = pipeline.find_supported_files(settings.docs_dir)

    available_files = [
        AvailableDocument(
            file_name=path.name,
            relative_path=str(path.relative_to(settings.docs_dir)),
            size_bytes=path.stat().st_size,
        )
        for path in files
    ]

    return DocumentsResponse(
        available_files=available_files,
        indexed_files=state.list_files(),
        chunk_count=vectorstore.count(),
    )


@router.post("/documents/upload/start", response_model=JobStartResponse)
async def upload_documents_start(
    files: list[UploadFile] = File(...),
    force_rebuild: bool = Form(False),
):
    """
    Start upload/index as a background job.

    The frontend should poll /api/jobs/{job_id}.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    saved_paths: list[Path] = []

    for upload in files:
        if not upload.filename:
            continue

        filename = validate_upload_filename(upload.filename)
        destination = resolve_upload_destination(
            filename=filename,
            force_rebuild=force_rebuild,
        )

        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        saved_paths.append(destination)

    if not saved_paths:
        raise HTTPException(
            status_code=400,
            detail="No valid files were uploaded.",
        )

    job_id = jobs.create(
        total=len(saved_paths),
        message=f"Queued upload indexing for {len(saved_paths)} file(s).",
    )

    thread = Thread(
        target=run_upload_job,
        args=(job_id, saved_paths, force_rebuild),
        daemon=True,
    )
    thread.start()

    return JobStartResponse(
        job_id=job_id,
        status_url=f"/api/jobs/{job_id}",
    )


@router.post("/documents/upload", response_model=ReindexResponse)
async def upload_documents_sync(
    files: list[UploadFile] = File(...),
    force_rebuild: bool = Form(False),
):
    """
    Synchronous compatibility endpoint.

    The UI should use /documents/upload/start for live progress.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    saved_paths: list[Path] = []

    for upload in files:
        if not upload.filename:
            continue

        filename = validate_upload_filename(upload.filename)
        destination = resolve_upload_destination(
            filename=filename,
            force_rebuild=force_rebuild,
        )

        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        saved_paths.append(destination)

    if not saved_paths:
        raise HTTPException(
            status_code=400,
            detail="No valid files were uploaded.",
        )

    pipeline = IngestionPipeline(settings)

    details: list[IngestResponse] = []
    indexed = 0
    skipped = 0
    total_chunks = 0

    for path in saved_paths:
        result = pipeline.ingest_file(path, force_rebuild=force_rebuild)
        details.append(result)

        if result.status == "indexed":
            indexed += 1
            total_chunks += result.chunks_added
        elif result.status == "skipped":
            skipped += 1

    return ReindexResponse(
        status="complete",
        files_seen=len(saved_paths),
        files_indexed=indexed,
        files_skipped=skipped,
        chunks_added=total_chunks,
        details=details,
    )


@router.post("/documents/reindex/start", response_model=JobStartResponse)
async def reindex_all_start(force_rebuild: bool = Form(False)):
    """
    Start full corpus reindex as a background job.
    """
    pipeline = IngestionPipeline(settings)
    paths = pipeline.find_supported_files(settings.docs_dir)

    if not paths:
        raise HTTPException(
            status_code=400,
            detail="No supported documents found.",
        )

    job_id = jobs.create(
        total=len(paths),
        message=f"Queued full reindex for {len(paths)} file(s).",
    )

    thread = Thread(
        target=run_reindex_job,
        args=(job_id, paths, force_rebuild),
        daemon=True,
    )
    thread.start()

    return JobStartResponse(
        job_id=job_id,
        status_url=f"/api/jobs/{job_id}",
    )


@router.post("/documents/reindex-selected/start", response_model=JobStartResponse)
async def reindex_selected_start(
    selected_files: list[str] = Form(...),
    force_rebuild: bool = Form(False),
):
    """
    Start selected-file reindex as a background job.
    """
    if not selected_files:
        raise HTTPException(status_code=400, detail="No files selected.")

    paths: list[Path] = []

    for relative in selected_files:
        path = (settings.docs_dir / relative).resolve()

        try:
            path.relative_to(settings.docs_dir.resolve())
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid path: {relative}",
            ) from exc

        if not path.exists() or not path.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {relative}",
            )

        if path.suffix.lower() not in DocumentLoader.SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {path.suffix.lower()}",
            )

        paths.append(path)

    job_id = jobs.create(
        total=len(paths),
        message=f"Queued selected reindex for {len(paths)} file(s).",
    )

    thread = Thread(
        target=run_reindex_job,
        args=(job_id, paths, force_rebuild),
        daemon=True,
    )
    thread.start()

    return JobStartResponse(
        job_id=job_id,
        status_url=f"/api/jobs/{job_id}",
    )


@router.post("/documents/reindex", response_model=ReindexResponse)
async def reindex_all_sync(force_rebuild: bool = Form(False)):
    """
    Synchronous compatibility endpoint.

    The UI should use /documents/reindex/start for live progress.
    """
    pipeline = IngestionPipeline(settings)
    return pipeline.ingest_directory(force_rebuild=force_rebuild)