from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..db import get_db
from .. import crud, storage, worker, schemas, tasks
import uuid, os
from pathlib import Path
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

    media_info = tasks.probe_media(str(dest))
    duration = media_info.get("duration") if media_info else None
    frame_rate = media_info.get("frame_rate") if media_info else None

    asset = crud.create_asset(
        db,
        filename=file.filename,
        master_path=str(dest),
        project_id=project_id,
        asset_type=asset_type,
        duration=duration,
        frame_rate=frame_rate,
        metadata=media_info or None,
    )
    # create proxy job
    job = crud.create_job(db, type="proxy", payload={"assets": [asset.id]}, project_id=asset.project_id)
    worker.enqueue_job(job.id)
    download_url = f"/upload/{asset.id}/file"
    return {
        "asset_id": asset.id,
        "master_path": asset.master_path,
        "asset_type": asset.asset_type,
        "project_id": asset.project_id,
        "proxy_job": job.id,
        "download_url": download_url,
        "duration": duration,
        "frame_rate": frame_rate,
    }


from ..schemas import AssetOut


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = crud.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset_out = schemas.AssetOut.model_validate(asset)
    asset_out.download_url = f"/upload/{asset.id}/file"
    return asset_out


@router.get("/{asset_id}/file")
def download_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = crud.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    path = Path(asset.master_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Asset file missing")

    media_type = storage.guess_mime_type(path)
    return FileResponse(path, media_type=media_type, filename=asset.filename or path.name)
    
