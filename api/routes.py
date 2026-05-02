import json
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
    QueryRequest,
    QueryResponse,
    ReindexResponse,
    RetrievedChunk,
    SettingsUpdate,
)
from config import settings
from core.document_loader import DocumentLoader
from core.generator import RAGGenerator
from core.ingestion import IngestionPipeline
from core.progress import jobs
from core.state import IndexState
from core.vectorstore import VectorStore
from eval.evaluator import Evaluator


router = APIRouter()


def safe_filename(filename: str) -> str:
    """
    Prevents path traversal from uploaded filenames.
    """
    return Path(filename).name


def validate_supported_document(filename: str) -> None:
    """
    Reject unsupported uploads before saving them.
    """
    extension = Path(filename).suffix.lower()

    if extension not in DocumentLoader.SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(DocumentLoader.SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}. Supported types: {allowed}",
        )


def serialize_model(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()

    if isinstance(model, dict):
        return model

    return jsonable_encoder(model)


def parse_jsonl_upload(content: bytes) -> list[dict[str, Any]]:
    """
    Parses uploaded JSONL evaluation files.
    """
    lines = content.decode("utf-8").splitlines()
    test_cases: list[dict[str, Any]] = []

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        try:
            test_cases.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON on line {line_number}: {exc}",
            ) from exc

    if not test_cases:
        raise HTTPException(
            status_code=400,
            detail="No test cases found in JSONL file.",
        )

    return test_cases


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


def run_evaluation_job(
    job_id: str,
    test_cases: list[dict[str, Any]],
    top_k: int,
    retrieval_only: bool,
) -> None:
    try:
        mode_label = "retrieval-only evaluation" if retrieval_only else "evaluation"

        jobs.update(
            job_id,
            status="running",
            current=0,
            total=len(test_cases),
            message=f"Starting {mode_label} for {len(test_cases)} test case(s).",
        )

        generator = RAGGenerator(settings)
        evaluator = Evaluator(generator)

        def progress(message: str, current: int, total: int) -> None:
            jobs.update(
                job_id,
                current=current,
                total=total,
                message=message,
            )

        summary = evaluator.run(
            test_cases=test_cases,
            top_k=top_k,
            retrieval_only=retrieval_only,
            progress_callback=progress,
        )

        jobs.succeed(job_id, summary.model_dump())

    except Exception as exc:
        jobs.fail(job_id, str(exc))


@router.get("/settings")
async def get_settings():
    return jsonable_encoder(
        {
            "app_name": settings.app_name,
            "app_env": settings.app_env,
            "docs_dir": settings.docs_dir,
            "chroma_dir": settings.chroma_dir,
            "index_state_path": settings.index_state_path,
            "collection_name": settings.collection_name,
            "index_version": settings.index_version,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "chat_provider": settings.chat_provider,
            "chat_model": settings.chat_model,
            "deepseek_base_url": settings.deepseek_base_url,
            "top_k_default": settings.top_k_default,
            "temperature_default": settings.temperature_default,
            "strictness_mode": settings.strictness_mode,
            "system_prompt": settings.system_prompt,
            "rag_instruction_template": settings.rag_instruction_template,
            "context_format": settings.context_format,
            "max_retrieval_distance": getattr(settings, "max_retrieval_distance", None),
            "reranker_enabled": getattr(settings, "reranker_enabled", None),
            "retrieval_candidate_k": getattr(settings, "retrieval_candidate_k", None),
            "rerank_top_k": getattr(settings, "rerank_top_k", None),
            "reranker_model": getattr(settings, "reranker_model", None),
        }
    )


@router.put("/settings")
async def update_settings(update: SettingsUpdate):
    """
    Only updates allowed runtime settings.

    Provider, chat model, and embedding model are intentionally locked.
    """
    update_data = update.model_dump(exclude_unset=True)

    if "top_k_default" in update_data and update_data["top_k_default"] is not None:
        settings.top_k_default = max(1, min(int(update_data["top_k_default"]), 50))

    if "temperature_default" in update_data and update_data["temperature_default"] is not None:
        settings.temperature_default = max(
            0.0,
            min(float(update_data["temperature_default"]), 2.0),
        )

    if "strictness_mode" in update_data and update_data["strictness_mode"] is not None:
        settings.strictness_mode = bool(update_data["strictness_mode"])

    if "system_prompt" in update_data and update_data["system_prompt"] is not None:
        settings.system_prompt = update_data["system_prompt"]

    if (
        "rag_instruction_template" in update_data
        and update_data["rag_instruction_template"] is not None
    ):
        template = update_data["rag_instruction_template"]

        if "{context}" not in template or "{question}" not in template:
            raise HTTPException(
                status_code=400,
                detail="RAG instruction template must include {context} and {question}.",
            )

        settings.rag_instruction_template = template

    return {
        "status": "updated",
        "settings": await get_settings(),
    }


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
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    saved_paths: list[Path] = []

    for upload in files:
        if not upload.filename:
            continue

        filename = safe_filename(upload.filename)
        validate_supported_document(filename)

        destination = settings.docs_dir / filename
        destination.parent.mkdir(parents=True, exist_ok=True)

        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        saved_paths.append(destination)

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No valid files were uploaded.")

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

    The UI uses /documents/upload/start for live progress.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    saved_paths: list[Path] = []

    for upload in files:
        if not upload.filename:
            continue

        filename = safe_filename(upload.filename)
        validate_supported_document(filename)

        destination = settings.docs_dir / filename
        destination.parent.mkdir(parents=True, exist_ok=True)

        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        saved_paths.append(destination)

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No valid files were uploaded.")

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
    pipeline = IngestionPipeline(settings)
    paths = pipeline.find_supported_files(settings.docs_dir)

    if not paths:
        raise HTTPException(status_code=400, detail="No supported documents found.")

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
            raise HTTPException(status_code=404, detail=f"File not found: {relative}")

        validate_supported_document(path.name)
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

    The UI uses /documents/reindex/start for live progress.
    """
    pipeline = IngestionPipeline(settings)
    return pipeline.ingest_directory(force_rebuild=force_rebuild)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = jobs.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    return job


@router.get("/jobs")
async def list_jobs():
    return {"jobs": jobs.list()}


@router.delete("/jobs/finished")
async def clear_finished_jobs():
    removed = jobs.clear_finished()
    return {"removed": removed}


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")

    generator = RAGGenerator(settings)

    result = generator.answer(
        question=req.question,
        top_k=req.top_k,
        temperature=req.temperature,
        strictness=req.strictness,
        system_prompt=req.system_prompt,
        rag_instruction_template=req.rag_instruction_template,
    )

    chunks_out = [
        RetrievedChunk(
            chunk_id=chunk["chunk_id"],
            text=chunk["text"],
            metadata=chunk["metadata"],
            distance=chunk["distance"],
        )
        for chunk in result["retrieved_chunks"]
    ]

    return QueryResponse(
        question=req.question,
        answer=result["answer"],
        retrieved_chunks=chunks_out,
    )


@router.post("/evaluate/run/start", response_model=JobStartResponse)
async def run_evaluation_start(
    file: UploadFile = File(...),
    top_k: int = Form(8),
    retrieval_only: bool = Form(False),
):
    if not file.filename or not file.filename.endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="Only .jsonl files are supported.")

    content = await file.read()
    test_cases = parse_jsonl_upload(content)

    mode_label = "retrieval-only evaluation" if retrieval_only else "evaluation"

    job_id = jobs.create(
        total=len(test_cases),
        message=f"Queued {mode_label} for {len(test_cases)} test case(s).",
    )

    thread = Thread(
        target=run_evaluation_job,
        args=(job_id, test_cases, top_k, retrieval_only),
        daemon=True,
    )
    thread.start()

    return JobStartResponse(
        job_id=job_id,
        status_url=f"/api/jobs/{job_id}",
    )


@router.post("/evaluate/run")
async def run_evaluation(
    file: UploadFile = File(...),
    top_k: int = Form(8),
    retrieval_only: bool = Form(False),
):
    """
    Synchronous compatibility endpoint.

    The UI uses /evaluate/run/start for live progress.
    """
    if not file.filename or not file.filename.endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="Only .jsonl files are supported.")

    content = await file.read()
    test_cases = parse_jsonl_upload(content)

    generator = RAGGenerator(settings)
    evaluator = Evaluator(generator)

    summary = evaluator.run(
        test_cases=test_cases,
        top_k=top_k,
        retrieval_only=retrieval_only,
    )

    return summary.model_dump()