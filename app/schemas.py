from pydantic import BaseModel, ConfigDict, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

class AssetCreate(BaseModel):
    filename: str
    project_id: Optional[str] = None

class AssetOut(BaseModel):
    id: str
    filename: str
    master_path: str
    proxy_path: Optional[str] = None
    asset_type: Optional[str] = "video"
    duration: Optional[float] = None
    frame_rate: Optional[float] = None
    download_url: Optional[str] = None

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
    remote_job_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def parse_json_payload(cls, data: Any) -> Any:
        if hasattr(data, 'payload') and isinstance(data.payload, str):
            # Create a mutable copy to modify
            if hasattr(data, '_mapping'): # SQLAlchemy model object
                mutable_data = dict(data._mapping)
            else: # Regular object
                mutable_data = data.__dict__.copy()
            
            try:
                mutable_data['payload'] = json.loads(mutable_data['payload'])
            except json.JSONDecodeError:
                mutable_data['payload'] = None # Or handle error appropriately
            return mutable_data
        return data


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

class TimelineStateUpdate(BaseModel):
    data: Dict[str, Any]


class TimelineStateOut(BaseModel):
    project_id: str
    data: Dict[str, Any]
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def parse_json_data(cls, data: Any) -> Any:
        if hasattr(data, 'data') and isinstance(data.data, str):
            # Create a mutable copy to modify
            if hasattr(data, '_mapping'): # SQLAlchemy model object
                mutable_data = dict(data._mapping)
            else: # Regular object
                mutable_data = data.__dict__.copy()
            
            mutable_data['data'] = json.loads(mutable_data['data'])
            return mutable_data
        return data

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
