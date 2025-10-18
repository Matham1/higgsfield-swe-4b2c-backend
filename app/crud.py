import json
import uuid
from sqlalchemy.orm import Session
from . import models, schemas

def create_asset(db: Session, filename: str, master_path: str, project_id: str = None):
    aid = uuid.uuid4().hex
    asset = models.Asset(id=aid, filename=filename, master_path=str(master_path), project_id=project_id)
    db.add(asset); db.commit(); db.refresh(asset)
    return asset

def get_asset(db: Session, asset_id: str):
    return db.query(models.Asset).get(asset_id)

def create_job(db: Session, type: str, payload: dict, project_id: str = None):
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