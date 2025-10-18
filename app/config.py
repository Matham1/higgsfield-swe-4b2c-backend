from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
SQLITE_URL = f"sqlite:///{BASE_DIR / 'storage' / 'app.db'}"

# For production, set FFMPEG_BIN in your environment if it's not in PATH
FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")

# For production, set these environment variables
HIGGSFIELD_API_BASE = os.environ.get("HIGGSFIELD_API_BASE", "https://api.higgsfield.ai")
HIGGSFIELD_API_KEY = os.environ.get("HIGGSFIELD_API_KEY", "")

# Number of worker threads to run for background jobs
WORKER_THREADS = int(os.getenv("WORKER_THREADS", "1"))
