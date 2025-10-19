from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..db import get_db # Your database dependency
from .. import crud, schemas 

router = APIRouter(prefix="/projects", tags=["projects"])
def get_current_user_id() -> str:
    return "mock-user-12345"


@router.post("/", response_model=schemas.Project, status_code=201)
def create_new_project(
    project_data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Creates a new video editing project for the authenticated user."""
    print(f"Creating project with name: {project_data.name} for user: {user_id}")  # Debug log
    
    db_project = crud.create_project(db=db, project=project_data, user_id=user_id)
    print(f"Created project with ID: {db_project.id}")  # Debug log
    
    if not db_project.id:
        raise HTTPException(status_code=500, detail="Failed to generate project ID")
        
    return db_project

@router.get("/", response_model=List[schemas.Project])
def get_projects(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    print(f"Fetching projects for user: {user_id}")  # Debug log
    projects = crud.get_projects_by_user(db=db, user_id=user_id)
    if not projects:
        raise HTTPException(status_code=404, detail="No projects found")
    return projects


@router.get("/{project_id}/timeline", response_model=schemas.TimelineStateOut)
def get_project_timeline(
    project_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    project = crud.get_project(db, project_id)
    if not project or project.user_id != user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    state = crud.get_timeline_state(db, project_id)
    if not state:
        return schemas.TimelineStateOut(project_id=project_id, data={}, updated_at=None)
    return schemas.TimelineStateOut.model_validate(state)


@router.put("/{project_id}/timeline", response_model=schemas.TimelineStateOut)
def upsert_project_timeline(
    project_id: str,
    payload: schemas.TimelineStateUpdate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    project = crud.get_project(db, project_id)
    if not project or project.user_id != user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    state = crud.upsert_timeline_state(db, project_id, payload.data)
    return schemas.TimelineStateOut.model_validate(state)
