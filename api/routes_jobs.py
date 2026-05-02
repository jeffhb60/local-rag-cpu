from fastapi import APIRouter, HTTPException
from core.progress import jobs

router = APIRouter(tags=["jobs"])

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