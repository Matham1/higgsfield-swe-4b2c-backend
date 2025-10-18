from pydantic import BaseModel
from typing import Optional, List, Dict

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
