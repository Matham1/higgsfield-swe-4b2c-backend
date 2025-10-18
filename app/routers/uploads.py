from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .. import crud, storage, worker, schemas
import uuid, os
from typing import List, Optional

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

@router.get(
    "/assests",
    response_model=List[schemas.AssetRead], # Use the new schema
    summary="Retrieve all assets and their IDs, optionally filtered by project."
)
def get_all_assets_endpoint(
    db: Session = Depends(get_db), 
    project_id: Optional[str] = None # Query parameter for filtering
):
    """
    Retrieves a list of all assets in the database.
    
    - **project_id (optional):** Filter assets to a specific project.
    
    Returns: A list of asset objects.
    """
    # 1. Call the CRUD function to get the data
    assets = crud.get_all_assets(db, project_id=project_id)
    
    # 2. Check if any assets were found (especially if filtered)
    if not assets and project_id:
        # Optional check: If a filter was applied and no assets found, 
        # return a 404, or return an empty list (200 OK) for an empty result.
        # Returning an empty list is often better for "get all" endpoints.
        return []
        
    # 3. Return the result. FastAPI handles the conversion to the response_model.
    return assets