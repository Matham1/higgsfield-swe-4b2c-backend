import json
import uuid
from sqlalchemy.orm import Session
from typing import Optional
from . import models, schemas


DEFAULT_PROJECT_NAME = "Default Project"
DEFAULT_PROJECT_USER = "system-default"


def _ensure_project(db: Session, project_id: Optional[str]) -> str:
    if project_id:
        return project_id

    project = (
        db.query(models.Project)
        .filter(models.Project.user_id == DEFAULT_PROJECT_USER, models.Project.name == DEFAULT_PROJECT_NAME)
        .first()
    )
    if not project:
        project = models.Project(
            id=uuid.uuid4().hex,
            name=DEFAULT_PROJECT_NAME,
            user_id=DEFAULT_PROJECT_USER,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
    return project.id


def create_asset(db: Session, filename: str, master_path: str, project_id: str = None, asset_type: str = "video"):
    project_id = _ensure_project(db, project_id)
    aid = uuid.uuid4().hex
    asset = models.Asset(
        id=aid,
        filename=filename,
        master_path=str(master_path),
        project_id=project_id,
        asset_type=asset_type,
    )
    db.add(asset); db.commit(); db.refresh(asset)
    return asset

def get_asset(db: Session, asset_id: str):
    return db.query(models.Asset).get(asset_id)

def create_job(db: Session, type: str, payload: dict, project_id: str = None):
    project_id = _ensure_project(db, project_id)
    jid = "job_" + uuid.uuid4().hex[:12]
    j = models.Job(id=jid, type=type, status="queued", payload=json.dumps(payload), project_id=project_id)
    db.add(j); db.commit(); db.refresh(j)
    return j

def update_job(db: Session, job_id: str, **fields):
    j = db.query(models.Job).get(job_id)
    if not j: return None
    for k,v in fields.items():
        if k == "payload":
            setattr(j, k, json.dumps(v))
        else:
            setattr(j, k, v)
    db.add(j); db.commit(); db.refresh(j)
    return j

def get_job(db: Session, job_id: str):
    return db.query(models.Job).get(job_id)

def list_jobs(db: Session, limit: int = 50):
    return db.query(models.Job).order_by(models.Job.created_at.desc()).limit(limit).all()

def create_project(db: Session, project: schemas.ProjectCreate, user_id: str):
    """Creates a new Project record in the database."""
    
    # 1. Create a unique ID
    project_id = uuid.uuid4().hex
    
    # 2. Instantiate the SQLAlchemy model
    db_project = models.Project(
        id=project_id,
        name=project.name,
        user_id=user_id # Essential: link the project to the owner
    )
    
    # 3. Add, commit, and refresh to get the generated timestamps
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    return db_project

def get_projects_by_user(db: Session, user_id: str):
    return db.query(models.Project).filter(models.Project.user_id == user_id).all()

def get_all_assets(db: Session, project_id: Optional[str] = None):
    """
    Retrieves all assets, optionally filtered by project_id.
    Returns a list of models.Asset objects.
    """
    query = db.query(models.Asset)
    
    # Apply optional filtering
    if project_id:
        query = query.filter(models.Asset.project_id == project_id)
        
    return query.all()
