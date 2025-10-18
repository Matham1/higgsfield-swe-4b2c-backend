from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .. import crud, worker
from ..schemas import JobCreate, JobOut
from typing import Dict

router = APIRouter(prefix="/renders", tags=["renders"])

@router.post("/", status_code=202)
def start_render(payload: JobCreate, db: Session = Depends(get_db)):
    job = crud.create_job(db, type=payload.type, payload=payload.payload, project_id=payload.project_id)
    worker.enqueue_job(job.id)
    return {"job_id": job.id}

@router.get("/{job_id}", response_model=JobOut)
def get_render_job(job_id: str, db: Session = Depends(get_db)):
    j = crud.get_job(db, job_id)
    if not j:
        return {"error": "not found"}
    return j
    j = crud.get_job(db, job_id)
    if not j:
        return {"error": "not found"}
    return {
        "id": j.id,
        "status": j.status,
        "progress": j.progress,
        "result_path": j.result_path,
        "logs": j.logs
    }
