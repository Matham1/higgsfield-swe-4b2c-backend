import threading, queue, time, json, os
from sqlalchemy.orm import Session
from .db import SessionLocal
from . import crud, tasks, higgsfield, render, hailuo
from .config import (
    STORAGE_DIR,
    HAILUO_DEFAULT_DURATION,
    PUBLIC_BASE_URL,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_ACCOUNT_ID,
    R2_PUBLIC_DOMAIN,
)
from typing import Dict
from pathlib import Path
import httpx
import boto3
from botocore.client import Config
import shutil
import mimetypes
import uuid
from urllib.parse import quote

job_q = queue.Queue()

_r2_client = None


def _get_r2_client():
    global _r2_client
    if _r2_client is not None:
        return _r2_client

    if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_ACCOUNT_ID, R2_PUBLIC_DOMAIN]):
        return None

    endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    session = boto3.session.Session()
    _r2_client = session.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4", region_name="auto"),
    )
    return _r2_client


def _publish_frame(path: Path) -> str:
    client = _get_r2_client()
    if client:
        key = f"hailuo/{uuid.uuid4().hex}_{path.name}"
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        client.upload_file(str(path), R2_BUCKET_NAME, key, ExtraArgs={"ContentType": content_type})
        base = R2_PUBLIC_DOMAIN.rstrip("/") if R2_PUBLIC_DOMAIN else ""
        if base and not base.startswith("http://") and not base.startswith("https://"):
            base = f"https://{base}"
        return f"{base}/{key}"

    return _to_public_url(path)

def enqueue_job(job_id: str):
    job_q.put(job_id)

def _to_public_url(path: Path) -> str:
    try:
        rel = path.relative_to(STORAGE_DIR)
    except ValueError:
        rel = path.name
    url_path = quote(str(rel).replace(os.sep, "/"))
    return f"{PUBLIC_BASE_URL.rstrip('/')}/storage/{url_path}"


def _prepare_frame(job_id: str, asset, *, start: bool) -> tuple[Path, bool]:
    tmp_dir = STORAGE_DIR / "frames"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(asset.master_path).suffix or ".jpg"
    frame_name = f"{job_id}_{'start' if start else 'end'}{suffix}"
    frame_path = tmp_dir / frame_name

    if asset.asset_type == "image":
        shutil.copy(asset.master_path, frame_path)
        return frame_path, True

    if asset.asset_type != "video":
        raise ValueError("Hailuo transition requires video or image assets")

    if start:
        tasks.extract_last_frame(asset.master_path, str(frame_path))
    else:
        tasks.extract_first_frame(asset.master_path, str(frame_path))

    return frame_path, True

def worker_loop():
    while True:
        job_id = job_q.get()
        db: Session = SessionLocal()
        try:
            job = crud.get_job(db, job_id)
            if not job or job.status not in ["queued", "waiting"]:
                db.close()
                job_q.task_done()
                continue

            crud.update_job(db, job.id, status="running")
            payload = json.loads(job.payload or "{}")

            if job.type == "proxy":
                assets = payload.get("assets", [])
                for i, aid in enumerate(assets):
                    asset = crud.get_asset(db, aid)
                    if not asset: continue
                    master = asset.master_path
                    proxy = master.replace("/assets/", "/assets/proxy_")
                    tasks.create_proxy(master, proxy)
                    asset.proxy_path = proxy
                    db.add(asset)
                    db.commit()
                    crud.update_job(db, job.id, progress=int(((i+1)/len(assets))*100))
                crud.update_job(db, job.id, status="completed", progress=100)

            elif job.type == "render":
                timeline = json.loads(job.payload)
                command, output_path = render.build_ffmpeg_command(db, timeline, job.id)
                logs = render.run_ffmpeg_render(command, job.id)
                crud.update_job(db, job.id, status="completed", progress=100, result_path=output_path, logs=logs)
            
            elif job.type == "higgsfield-generate":
                # Example of a generative task
                # 1. Get input asset URL (requires serving files or pre-uploading)
                # 2. Call higgsfield API
                # 3. Download result and create a new asset
                # This is a simplified async-in-sync call.
                # A real implementation might need polling.
                import asyncio
                input_url = payload.get("input_url") # e.g. http://host.docker.internal:8000/files/assets/....
                params = payload.get("params", {})
                result = asyncio.run(higgsfield.call_higgsfield_generate(input_url, params))
                # Assume result is {'status':'done','result_url': '...'}
                # TODO: download result_url, save as new asset, update job with asset_id
                crud.update_job(db, job.id, status="completed", progress=100, payload={"result": result})

            elif job.type == "hailuo-transition":
                from_asset_id = payload.get("from_asset_id")
                to_asset_id = payload.get("to_asset_id")
                prompt = payload.get("prompt") or "Seamless cinematic cut"
                motion_id = payload.get("motion_id")
                duration = int(payload.get("duration") or HAILUO_DEFAULT_DURATION)
                resolution = str(payload.get("resolution") or "768")
                enhance_prompt = bool(payload.get("enhance_prompt", True))
                hailuo_request = None

                if not motion_id:
                    raise ValueError("Hailuo transition requires motion_id")

                from_asset = crud.get_asset(db, from_asset_id)
                to_asset = crud.get_asset(db, to_asset_id)
                if not from_asset or not to_asset:
                    raise ValueError("Missing source assets for Hailuo transition")

                start_frame_path, cleanup_start = _prepare_frame(job.id, from_asset, start=True)
                end_frame_path, cleanup_end = _prepare_frame(job.id, to_asset, start=False)

                start_url = _publish_frame(start_frame_path)
                end_url = _publish_frame(end_frame_path)

                hailuo_request = {
                    "start_image_url": start_url,
                    "end_image_url": end_url,
                    "prompt": prompt,
                    "duration": duration,
                    "motion_id": motion_id,
                    "resolution": resolution,
                    "enhance_prompt": enhance_prompt,
                }

                result = hailuo.run_transition(**hailuo_request)

                result_url = result.get("result_url")
                if not result_url:
                    raise RuntimeError("Hailuo did not return a downloadable result URL")

                output_dir = STORAGE_DIR / "assets"
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{job.id}_hailuo_transition.mp4"
                with httpx.Client(timeout=120) as client:
                    resp = client.get(result_url)
                    resp.raise_for_status()
                    output_path.write_bytes(resp.content)

                new_asset = crud.create_asset(
                    db,
                    filename=output_path.name,
                    master_path=str(output_path),
                    project_id=job.project_id,
                )

                crud.update_job(
                    db,
                    job.id,
                    status="completed",
                    progress=100,
                    result_path=str(output_path),
                    payload={
                        "hailuo_job_set_id": result.get("job_set_id"),
                        "hailuo_request": hailuo_request,
                        "asset_id": new_asset.id,
                    },
                )

                # Clean up temp frames
                for frame_path, should_cleanup in ((start_frame_path, cleanup_start), (end_frame_path, cleanup_end)):
                    if should_cleanup:
                        try:
                            Path(frame_path).unlink(missing_ok=True)
                        except OSError:
                            pass

            else:
                crud.update_job(db, job.id, status="failed", logs=f"unknown job type: {job.type}")

        except Exception as e:
            error_log = {
                "error": str(e),
            }
            if job.type == "hailuo-transition" and 'hailuo_request' in locals() and hailuo_request:
                error_log["hailuo_request"] = hailuo_request
            crud.update_job(db, job_id, status="failed", logs=json.dumps(error_log))
        finally:
            db.close()
            job_q.task_done()
        
        time.sleep(0.1)

def start_worker_thread():
    from .config import WORKER_THREADS
    for i in range(WORKER_THREADS):
        t = threading.Thread(target=worker_loop, daemon=True, name=f"Worker-{i}")
        t.start()
