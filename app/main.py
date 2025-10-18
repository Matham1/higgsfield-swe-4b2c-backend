import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .db import init_db
from .worker import start_worker_thread
from .routers import uploads, renders, jobs, projects, transitions
from .config import STORAGE_DIR
import os

app = FastAPI(title="Video Editor Prototype")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(uploads.router)
app.include_router(renders.router)
app.include_router(jobs.router)
app.include_router(projects.router)
app.include_router(transitions.router)

app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

@app.on_event("startup")
def startup():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    start_worker_thread()

@app.get("/")
def root():
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
