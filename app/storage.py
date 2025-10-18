import os
import mimetypes
from pathlib import Path
from shutil import copyfileobj
from .config import STORAGE_DIR

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

def save_upload_stream(upload_file, dest_subdir="assets"):
    dest_dir = STORAGE_DIR / dest_subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    file_id = upload_file.filename
    # create unique filename; here we use filename prefixed by uuid if needed in caller
    dest_path = dest_dir / file_id
    with open(dest_path, "wb") as dst:
        copyfileobj(upload_file.file, dst)
    return str(dest_path)

def ensure_dir(path: str):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def guess_mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"
