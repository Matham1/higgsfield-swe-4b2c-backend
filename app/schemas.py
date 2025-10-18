from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class AssetCreate(BaseModel):
    filename: str
    project_id: Optional[str] = None

class AssetOut(BaseModel):
    id: str
    filename: str
    master_path: str
    proxy_path: Optional[str] = None

class JobCreate(BaseModel):
    project_id: Optional[str]
    type: str
    payload: Dict  # timeline / list of asset ids, effects etc.

class JobOut(BaseModel):
    id: str
    project_id: Optional[str] = None
    type: str
    status: str
    progress: int
    result_path: Optional[str] = None
    logs: Optional[str] = None


class ProjectBase(BaseModel):
    """Base schema for project creation/update (input)."""
    name: str = "Untitled Project"

class ProjectCreate(ProjectBase):
    """Schema used when creating a new project."""
    # We expect the user_id to be injected by authentication dependency, not the user
    pass 

class Project(ProjectBase):
    """Schema used for returning a project (output)."""
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        # Allows conversion from SQLAlchemy models
        from_attributes = True