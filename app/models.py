from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .db import Base
from sqlalchemy import Column, String, Float, Text, DateTime, Boolean, func

class Project(Base):
    """Represents a single video editing project."""
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False) # RESTORED: Added for project ownership
    name = Column(String, default="Untitled Project", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to Assets: A Project has many Assets
    assets = relationship("Asset", back_populates="project")
    
    # Relationship to Jobs: A Project may have multiple rendering/proxy jobs
    jobs = relationship("Job", back_populates="project")
    timeline = relationship("TimelineState", back_populates="project", uselist=False, cascade="all, delete-orphan")


class Asset(Base):
    """Represents a single media file (video, audio, or image) used in a project."""
    __tablename__ = "assets"
    
    # Core Identification and Linking
    id = Column(String, primary_key=True, index=True)
    
    # Foreign Key linking this asset to a project
    # project_id should be NOT NULL if an asset must belong to a project
    project_id = Column(String, ForeignKey("projects.id"), index=True, nullable=False)

    # File Information
    filename = Column(String, nullable=False)         # Original filename on upload
    asset_type = Column(String, default="video")      # 'video', 'audio', 'image'
    
    # Paths (Crucial for FFmpeg)
    master_path = Column(String, nullable=False)      # Storage path to high-res master file
    proxy_path = Column(String, nullable=True)        # Path to low-res proxy file

    # Technical Details (Required for Editing Logic, set after FFprobe)
    duration = Column(Float, nullable=True)           # Duration in seconds (use Float for precision)
    frame_rate = Column(Float, nullable=True)         # Original FPS (e.g., 29.97)
    original_width = Column(String, nullable=True)    # Store as string if you encounter fractional resolutions
    original_height = Column(String, nullable=True)
    
    # Metadata and Status
    metadata_json = Column("metadata", Text, nullable=True) # Full FFprobe output
    is_available = Column(Boolean, default=True)      # Check file existence

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to the Project
    project = relationship("Project", back_populates="assets")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), index=True, nullable=True) 
    type = Column(String, nullable=False)             # e.g., "render", "proxy"
    status = Column(String, nullable=False, default="queued")
    progress = Column(Integer, default=0)             # 0..100
    payload = Column(Text, nullable=True)             # JSON text describing timeline or assets
    result_path = Column(String, nullable=True)       # path to final mp4
    logs = Column(Text, nullable=True)                # json list or plain text
    remote_job_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    project = relationship("Project", back_populates="jobs")


class TimelineState(Base):
    __tablename__ = "timelines"

    project_id = Column(String, ForeignKey("projects.id"), primary_key=True)
    data = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="timeline")
