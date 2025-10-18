# Project Overview

## Backend Summary

- **Framework & Runtime**: FastAPI application served by Uvicorn, using SQLite via SQLAlchemy ORM.
- **Purpose**: Accept video uploads, generate proxy clips, and concatenate assets into renders via background workers.
- **Key Modules**:
  - `app/main.py`: Bootstraps FastAPI, database, storage directory, and worker thread.
  - `app/routers/`: API endpoints for uploads, renders, and job inspection.
  - `app/worker.py`: In-process worker consuming a queue to run ffmpeg-based tasks.
  - `app/tasks.py`: ffmpeg helpers for proxy generation and concatenation.

## Current Issues & Risks

- Upload and render routers contain duplicated, unreachable return blocks—clean-up needed for clarity.
- Routers return SQLAlchemy models without enabling Pydantic ORM mode, which will raise response validation errors.
- Upload path reads entire file into memory before writing; large files can exhaust RAM—stream uploads instead.
- Worker queue is in-memory; jobs disappear on process restart and can't scale across instances.
- `concat_files_reencode` assumes every input includes audio, which can break when assets are silent.

## Suggested Next Steps

1. Enable Pydantic `model_config = ConfigDict(from_attributes=True)` (or equivalent) on response models and remove duplicate return code.
2. Replace eager upload reads with streaming writes (reuse helpers in `storage.py`).
3. Consider durable job backend (Redis/RQ/Celery) and improve job logging/error handling.
4. Harden ffmpeg tasks to handle assets lacking audio streams and add smoke tests for key API flows.
