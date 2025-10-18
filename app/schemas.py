from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class AssetCreate(BaseModel):
    filename: str
    project_id: Optional[str] = None

class AssetOut(BaseModel):
    id: str
    filename: str
    master_path: str
    proxy_path: Optional[str] = None
    asset_type: Optional[str] = "video"

    model_config = ConfigDict(from_attributes=True)

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
    payload: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class Effect(BaseModel):
    name: str
    parameters: Dict

class Transition(BaseModel):
    type: str
    duration: float
    applies_to_clip_id: str

class Clip(BaseModel):
    asset_id: str
    track_start: float
    track_end: float
    source_in: float
    source_out: float
    effects: Optional[List[Effect]] = None
    transition: Optional[Transition] = None

class Track(BaseModel):
    id: str
    type: str
    clips: List[Clip]

class OutputSettings(BaseModel):
    output_filename: str
    output_format: str
    video_codec: str
    audio_codec: str
    resolution: str
    framerate: int
    bitrate: Optional[str] = None

class Timeline(BaseModel):
    output_settings: OutputSettings
    tracks: List[Track]

class RenderCreate(BaseModel):
    project_id: str
    timeline: Timeline

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

class AssetRead(BaseModel):
    """Schema for returning asset details, including the project_id."""
    id: str
    project_id: str
    filename: str
    asset_type: str
    master_path: str
    proxy_path: Optional[str] = None
    duration: Optional[float] = None
    frame_rate: Optional[float] = None
    original_width: Optional[str] = None
    original_height: Optional[str] = None
    is_available: bool
    
    class Config:
        from_attributes = True



class HailuoTransitionRequest(BaseModel):
    project_id: Optional[str] = None
    from_asset_id: str
    to_asset_id: str
    prompt: str
    motion_id: str
    duration: Optional[int] = None
    resolution: Optional[str] = "768"
    enhance_prompt: Optional[bool] = True
