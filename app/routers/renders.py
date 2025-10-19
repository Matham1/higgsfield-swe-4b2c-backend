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
    return _start_render_job(db, payload.project_id, preview=False)


@router.post("/preview", status_code=202, response_model=JobOut)
def start_preview_render(payload: RenderCreate, db: Session = Depends(get_db)):
    """Starts a fast preview render job using proxy assets."""
    return _start_render_job(db, payload.project_id, preview=True)


def _start_render_job(db: Session, project_id: str, preview: bool):
    """Helper to start a render or preview render job."""
    timeline_state = crud.get_timeline_state(db, project_id)
    if not timeline_state:
        raise HTTPException(
            status_code=404,
            detail=f"No timeline found for project {project_id}. Please save a timeline first.",
        )

    timeline_data = json.loads(timeline_state.data)
    job_type = "preview-render" if preview else "render"

    job = crud.create_job(db, type=job_type, payload=timeline_data, project_id=project_id)
    worker.enqueue_job(job.id)
    return job


@router.get("/{job_id}", response_model=JobOut)
def get_render_job(job_id: str, db: Session = Depends(get_db)):
    j = crud.get_job(db, job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return j
