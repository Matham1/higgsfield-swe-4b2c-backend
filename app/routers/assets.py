from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from .. import crud, schemas

router = APIRouter(prefix="/assets", tags=["assets"])

@router.get(
    "/",
    response_model=List[schemas.AssetRead], # Use the new schema
    summary="Retrieve all assets and their IDs, optionally filtered by project."
)
def get_all_assets_endpoint(
    db: Session = Depends(get_db), 
    project_id: Optional[str] = None # Query parameter for filtering
):
    """
    Retrieves a list of all assets in the database.
    
    - project_id (optional): Filter assets to a specific project.
    
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
