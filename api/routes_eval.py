import json
from threading import Thread
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.schemas import JobStartResponse
from config import settings
from core.generator import RAGGenerator
from core.progress import jobs
from eval.evaluator import Evaluator


router = APIRouter(tags=["evaluation"])


def parse_jsonl_content(content: bytes, filename: str | None = None) -> list[dict[str, Any]]:
    """
    Parse uploaded JSONL evaluation content.

    Each non-empty line must be valid JSON.
    """
    if filename and not filename.endswith(".jsonl"):
        raise HTTPException(
            status_code=400,
            detail="Only .jsonl files are supported.",
        )

    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not decode file as UTF-8: {exc}",
        ) from exc

    test_cases: list[dict[str, Any]] = []

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON on line {line_number}: {exc}",
            ) from exc

        if not isinstance(parsed, dict):
            raise HTTPException(
                status_code=400,
                detail=f"Line {line_number} must be a JSON object.",
            )

        if "question" not in parsed or not str(parsed["question"]).strip():
            raise HTTPException(
                status_code=400,
                detail=f"Line {line_number} is missing a non-empty question.",
            )

        test_cases.append(parsed)

    if not test_cases:
        raise HTTPException(
            status_code=400,
            detail="No test cases found in JSONL file.",
        )

    return test_cases


def run_evaluation_job(
    job_id: str,
    test_cases: list[dict[str, Any]],
    top_k: int,
) -> None:
    try:
        jobs.update(
            job_id,
            status="running",
            current=0,
            total=len(test_cases),
            message=f"Starting evaluation for {len(test_cases)} test case(s).",
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
            progress_callback=progress,
        )

        jobs.succeed(job_id, summary.model_dump())

    except Exception as exc:
        jobs.fail(job_id, str(exc))


@router.post("/evaluate/run/start", response_model=JobStartResponse)
async def run_evaluation_start(
    file: UploadFile = File(...),
    top_k: int = Form(8),
):
    """
    Start evaluation as a background job.

    The frontend should poll /api/jobs/{job_id}.
    """
    content = await file.read()
    test_cases = parse_jsonl_content(content=content, filename=file.filename)

    job_id = jobs.create(
        total=len(test_cases),
        message=f"Queued evaluation for {len(test_cases)} test case(s).",
    )

    thread = Thread(
        target=run_evaluation_job,
        args=(job_id, test_cases, top_k),
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
):
    """
    Synchronous compatibility endpoint.

    The UI should use /evaluate/run/start for live progress.
    """
    content = await file.read()
    test_cases = parse_jsonl_content(content=content, filename=file.filename)

    generator = RAGGenerator(settings)
    evaluator = Evaluator(generator)

    summary = evaluator.run(
        test_cases=test_cases,
        top_k=top_k,
    )

    return summary.model_dump()