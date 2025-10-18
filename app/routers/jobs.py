from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import crud
from ..schemas import JobOut
from typing import List

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/", response_model=List[JobOut])
def list_jobs(db: Session = Depends(get_db), limit: int = 50):
    """List recent jobs."""
    return crud.list_jobs(db, limit=limit)

@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get job details."""
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
