import json
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import (
    BASE_DIR,
    HIGGSFIELD_API_KEY,
    HIGGSFIELD_API_SECRET,
    HIGGSFIELD_MOTIONS_ENDPOINT,
)
from ..db import get_db
from .. import crud, worker
from ..schemas import HailuoTransitionRequest

router = APIRouter(prefix="/transitions", tags=["transitions"])

MOTIONS_FILE = BASE_DIR / "docs" / "hailuo" / "motions.json"


@lru_cache(maxsize=1)
def _load_motions() -> List[Dict[str, Any]]:
    remote = _fetch_remote_motions()
    if remote:
        return remote

    try:
        return json.loads(MOTIONS_FILE.read_text())
    except FileNotFoundError:
        return []


def _fetch_remote_motions() -> List[Dict[str, Any]]:
    if not (HIGGSFIELD_API_KEY and HIGGSFIELD_API_SECRET and HIGGSFIELD_MOTIONS_ENDPOINT):
        return []

    try:
        resp = httpx.get(
            HIGGSFIELD_MOTIONS_ENDPOINT,
            headers={
                "hf-api-key": HIGGSFIELD_API_KEY,
                "hf-secret": HIGGSFIELD_API_SECRET,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "items" in data:
            data = data.get("items")
        if isinstance(data, list):
            return data
    except Exception:
        pass
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
