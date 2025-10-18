from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
STORAGE_DIR = BASE_DIR / "storage"
SQLITE_URL = f"sqlite:///{BASE_DIR / 'storage' / 'app.db'}"

# For production, set FFMPEG_BIN in your environment if it's not in PATH
FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")

# For production, set these environment variables
# Higgsfield platform (Minimax Hailuo lives here)
HIGGSFIELD_API_BASE = os.environ.get("HIGGSFIELD_API_BASE", "https://api.higgsfield.ai")
HIGGSFIELD_PLATFORM_BASE = os.environ.get("HIGGSFIELD_PLATFORM_BASE", "https://platform.higgsfield.ai")
HIGGSFIELD_API_KEY = os.environ.get("HIGGSFIELD_API_KEY", "")
HIGGSFIELD_API_SECRET = os.environ.get("HIGGSFIELD_API_SECRET", "")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")

R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME")
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
R2_PUBLIC_DOMAIN = os.environ.get("R2_PUBLIC_DOMAIN")

# Hailuo specific knobs (defaults fall back to general Higgsfield values)
HAILUO_MODEL_ID = os.environ.get("HAILUO_MODEL_ID", "")
HIGGSFIELD_MOTIONS_ENDPOINT = os.environ.get(
    "HIGGSFIELD_MOTIONS_ENDPOINT",
    f"{HIGGSFIELD_PLATFORM_BASE.rstrip('/')}/v1/motions",
)
HAILUO_DEFAULT_DURATION = int(os.environ.get("HAILUO_DEFAULT_DURATION", "2"))
HAILUO_ENDPOINT = os.environ.get("HAILUO_ENDPOINT", "/v1/image2video/minimax")
HAILUO_TIMEOUT = float(os.environ.get("HAILUO_TIMEOUT", "300"))
HAILUO_POLL_INTERVAL = float(os.environ.get("HAILUO_POLL_INTERVAL", "3"))
HAILUO_MAX_POLLS = int(os.environ.get("HAILUO_MAX_POLLS", "0"))

# Number of worker threads to run for background jobs
WORKER_THREADS = int(os.getenv("WORKER_THREADS", "1"))
