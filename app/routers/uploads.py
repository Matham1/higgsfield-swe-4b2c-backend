from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import crud, storage, worker, schemas
import uuid, os
from typing import List, Optional

router = APIRouter(prefix="/upload", tags=["uploads"])

CHUNK_SIZE = 1024 * 1024  # 1MB

@router.post("/")
async def upload_file(file: UploadFile = File(...), project_id: str = None, db: Session = Depends(get_db)):
    # create deterministic unique filename
    uid = uuid.uuid4().hex
    ext = os.path.splitext(file.filename)[1] or ".mp4"
    fname = uid + ext
    dest = storage.STORAGE_DIR / "assets" / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    # save file in streaming chunks to avoid loading large files into memory
    size = 0
    with open(dest, "wb") as buffer:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            buffer.write(chunk)
    await file.seek(0)
    # create DB record
    asset_type = "video"
    if file.content_type:
        if file.content_type.startswith("image/"):
            asset_type = "image"
        elif file.content_type.startswith("audio/"):
            asset_type = "audio"

    asset = crud.create_asset(
        db,
        filename=file.filename,
        master_path=str(dest),
        project_id=project_id,
        asset_type=asset_type,
    )
    # create proxy job
    job = crud.create_job(db, type="proxy", payload={"assets": [asset.id]}, project_id=asset.project_id)
    worker.enqueue_job(job.id)
    return {
        "asset_id": asset.id,
        "master_path": asset.master_path,
        "asset_type": asset.asset_type,
        "project_id": asset.project_id,
        "proxy_job": job.id,
    }


from ..schemas import AssetOut


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = crud.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
    
