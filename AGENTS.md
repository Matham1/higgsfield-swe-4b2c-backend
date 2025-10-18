# Repository Guidelines

## Project Structure & Module Organization

The repository is a **FastAPI-based backend** built around modular components:

- **`app/main.py`** — Initializes the FastAPI app, database, storage, and worker thread.  
- **`app/routers/`** — Contains route definitions for uploads, render operations, and job inspection endpoints.  
- **`app/worker.py`** — Background worker that processes queued video jobs using `ffmpeg`.  
- **`app/tasks.py`** — Helper utilities for proxy generation and concatenation.  
- **`app/models/`** — SQLAlchemy ORM models that define database tables.  
- **`tests/`** — Unit tests validating API endpoints and worker behavior.  
- **`assets/`** — Sample media files for local development.

Follow this structure when contributing new features or modules.

---

## Build, Test, and Development Commands

Use a Python 3.11+ virtual environment. Common commands:

```bash
uvicorn app.main:app --reload        # Run development server
pytest -v                            # Run test suite
black . && isort .                   # Format and sort imports
```

- **Indentation**: 4 spaces.  
- **Naming**: use `snake_case` for files/functions, `CamelCase` for classes.  
- **Tests**: place under `tests/` with `test_` prefix (e.g., `test_upload.py`).  

To rebuild dependencies:

```bash
pip install -r requirements.txt
```

---

## Commit & Pull Request Standards

- **Commit messages** follow *conventional commits*:  
  `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.  
  Example:

  ```bash
  feat(worker): add audio stream fallback for silent clips
  ```

- **Pull Requests** must include:  
  - A clear summary of the change.  
  - Linked issue number(s).  
  - Screenshots or logs if UI/API behavior changes.  
  - Passing CI checks (lint + tests).  

---

## Security & Configuration Tips

- Store sensitive keys (e.g., `hf-api-key`, `hf-secret`) in `.env`; never commit credentials.  
- Use HTTPS for webhook endpoints (`/v1/speak/higgsfield`, `/v1/image2video/dop`).  
- Validate webhook signatures with the `X-Webhook-Secret-Key` header.  
- Prefer streaming uploads to avoid memory exhaustion on large files.  

---

## Agent-Specific Notes

When integrating Higgsfield API endpoints:

- Use the correct **model IDs** (`dop-lite`, `soul`, `speak-v2`).  
- Poll `/v1/job-sets/{id}` for job completion or use webhooks.  
- Cache style/motion lists locally for efficiency.  

---

✅ *Contributors are encouraged to maintain code readability, security hygiene, and consistent commit history.*
