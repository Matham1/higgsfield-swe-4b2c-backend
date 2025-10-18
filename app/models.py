from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.sql import func
from .db import Base

class Asset(Base):
    __tablename__ = "assets"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, index=True, nullable=True)
    filename = Column(String, nullable=False)         # original filename
    master_path = Column(String, nullable=False)      # storage path to master file
    proxy_path = Column(String, nullable=True)        # path to proxy file
    duration = Column(Integer, nullable=True)         # seconds (optional)
    metadata_json = Column("metadata", Text, nullable=True)            # free form JSON text
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, index=True, nullable=True)
    type = Column(String, nullable=False)             # e.g., "render", "proxy"
    status = Column(String, nullable=False, default="queued")
    progress = Column(Integer, default=0)             # 0..100
    payload = Column(Text, nullable=True)             # JSON text describing timeline or assets
    result_path = Column(String, nullable=True)       # path to final mp4
    logs = Column(Text, nullable=True)                # json list or plain text
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
