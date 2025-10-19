from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import crud, worker
from ..schemas import JobCreate, JobOut, RenderCreate
from typing import Dict
import json

router = APIRouter(prefix="/renders", tags=["renders"])

@router.post("/", status_code=202, response_model=JobOut)
def start_render(payload: RenderCreate, db: Session = Depends(get_db)):
    timeline_state = crud.get_timeline_state(db, payload.project_id)
    if not timeline_state:
        raise HTTPException(
            status_code=404, 
            detail=f"No timeline found for project {payload.project_id}. Please save a timeline first."
        )

    timeline_data = json.loads(timeline_state.data)

    job = crud.create_job(
        db, 
        type="render", 
        payload=timeline_data, 
        project_id=payload.project_id
    )
    worker.enqueue_job(job.id)
    return job

@router.get("/{job_id}", response_model=JobOut)
def get_render_job(job_id: str, db: Session = Depends(get_db)):
    j = crud.get_job(db, job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return j
