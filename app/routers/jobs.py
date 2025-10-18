from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import crud, models
from ..schemas import JobOut
from typing import List
import json

router = APIRouter(prefix="/jobs", tags=["jobs"])

def serialize_job(job: models.Job) -> JobOut:
    payload = None
    if job.payload:
        try:
            payload = json.loads(job.payload)
        except json.JSONDecodeError:
            payload = None

    return JobOut(
        id=job.id,
        project_id=job.project_id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        result_path=job.result_path,
        logs=job.logs,
        payload=payload,
    )


@router.get("/", response_model=List[JobOut])
def list_jobs(db: Session = Depends(get_db), limit: int = 50):
    """List recent jobs."""
    jobs = crud.list_jobs(db, limit=limit)
    return [serialize_job(job) for job in jobs]

@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get job details."""
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize_job(job)
