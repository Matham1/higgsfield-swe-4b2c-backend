from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .. import crud, storage, worker
import uuid, os

router = APIRouter(prefix="/upload", tags=["uploads"])

@router.post("/")
async def upload_file(file: UploadFile = File(...), project_id: str = None, db: Session = Depends(get_db)):
    # create deterministic unique filename
    uid = uuid.uuid4().hex
    ext = os.path.splitext(file.filename)[1] or ".mp4"
    fname = uid + ext
    dest = storage.STORAGE_DIR / "assets" / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    # save file
    with open(dest, "wb") as f:
        contents = await file.read()
        f.write(contents)
    # create DB record
    asset = crud.create_asset(db, filename=file.filename, master_path=str(dest), project_id=project_id)
    # create proxy job
    job = crud.create_job(db, type="proxy", payload={"assets":[asset.id]}, project_id=project_id)
    worker.enqueue_job(job.id)
    return {"asset_id": asset.id, "master_path": asset.master_path, "proxy_job": job.id}
    # create proxy job
    job = crud.create_job(db, type="proxy", payload={"assets":[asset.id]}, project_id=project_id)
    worker.enqueue_job(job.id)
    return {"asset_id": asset.id, "master_path": asset.master_path, "proxy_job": job.id}
