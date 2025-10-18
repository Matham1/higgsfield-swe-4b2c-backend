from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db # Your database dependency
from .. import crud, schemas 

router = APIRouter(prefix="/projects", tags=["projects"])
def get_current_user_id() -> str:
    return "mock-user-12345"


@router.post("/", response_model=schemas.Project, status_code=201)
def create_new_project(
    project_data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id) # Inject the owner ID
):
    """
    Creates a new video editing project for the authenticated user.
    """

    # 1. Call the CRUD function to save the project
    db_project = crud.create_project(
        db=db, 
        project=project_data, 
        user_id=user_id
    )
    
    # 2. Return the created project object
    return db_project
