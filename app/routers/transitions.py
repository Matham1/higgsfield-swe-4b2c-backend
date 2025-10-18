import json
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import BASE_DIR
from ..db import get_db
from .. import crud, worker
from ..schemas import HailuoTransitionRequest

router = APIRouter(prefix="/transitions", tags=["transitions"])

MOTIONS_FILE = BASE_DIR / "docs" / "hailuo" / "motions.json"


def _load_motions() -> List[Dict[str, Any]]:
    version = None
    try:
        version = MOTIONS_FILE.stat().st_mtime_ns
    except FileNotFoundError:
        version = None
    return _load_motions_cached(version)


@lru_cache(maxsize=4)
def _load_motions_cached(_version_key: Optional[int]) -> List[Dict[str, Any]]:
    try:
        return json.loads(MOTIONS_FILE.read_text())
    except FileNotFoundError:
        return []


@router.get("/hailuo/motions")
def list_hailuo_motions():
    return _load_motions()


@router.post("/hailuo", status_code=202)
def create_hailuo_transition(request: HailuoTransitionRequest, db: Session = Depends(get_db)):
    from_asset = crud.get_asset(db, request.from_asset_id)
    to_asset = crud.get_asset(db, request.to_asset_id)

    if not from_asset or not to_asset:
        raise HTTPException(status_code=404, detail="Source assets not found")

    if not request.motion_id:
        raise HTTPException(status_code=400, detail="motion_id is required")

    motion_ids = {motion.get("id") for motion in _load_motions() if isinstance(motion, dict)}
    # If the provided motion id isn't in our cached list, allow it to pass through.
    # Higgsfield periodically rolls out new presets; logging helps diagnose mismatches.
    if motion_ids and request.motion_id not in motion_ids:
        print(f"[hailuo] motion_id {request.motion_id} not in cached catalogue ({len(motion_ids)} entries)")

    if request.project_id and (
        from_asset.project_id != request.project_id or to_asset.project_id != request.project_id
    ):
        raise HTTPException(status_code=400, detail="Assets do not belong to the specified project")

    project_id = request.project_id or from_asset.project_id or to_asset.project_id

    job_payload = {
        "from_asset_id": from_asset.id,
        "to_asset_id": to_asset.id,
        "prompt": request.prompt,
        "motion_id": request.motion_id,
        "duration": request.duration,
        "resolution": request.resolution,
        "enhance_prompt": request.enhance_prompt,
    }

    job = crud.create_job(db, type="hailuo-transition", payload=job_payload, project_id=project_id)
    worker.enqueue_job(job.id)
    return {"job_id": job.id}
