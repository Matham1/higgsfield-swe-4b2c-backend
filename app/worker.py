import threading, queue, time, json, os
import concurrent.futures
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
    HAILUO_TIMEOUT,
    HAILUO_POLL_INTERVAL,
    HAILUO_MAX_POLLS,
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
hailuo_poll_q = queue.Queue()

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


def _enqueue_hailuo_poll(job_id: str):
    hailuo_poll_q.put(job_id)

def _to_public_url(path: Path) -> str:
    try:
        rel = path.relative_to(STORAGE_DIR)
    except ValueError:
        rel = path.name
    rel_str = str(rel).replace(os.sep, "/")
    if rel_str.startswith("frames/"):
        frame_path = rel_str[len("frames/") :]
        return f"{PUBLIC_BASE_URL.rstrip('/')}/frames/{quote(frame_path)}"
    raise RuntimeError(f"Unsupported public URL path: {path}")


def _prepare_frame(job_id: str, asset, *, start: bool) -> tuple[Path, bool]:
    tmp_dir = STORAGE_DIR / "frames"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    if asset.asset_type == "video":
        suffix = ".jpg"
    else:
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

def _restore_pending_jobs():
    from . import models

    db: Session = SessionLocal()
    try:
        pending = (
            db.query(models.Job)
            .filter(models.Job.status.in_(["queued", "waiting", "running"]))
            .order_by(models.Job.created_at.asc())
            .all()
        )
        for job in pending:
            if job.type == "hailuo-transition" and (job.remote_job_id or (job.payload and "hailuo_job_set_id" in (json.loads(job.payload or "{}") or {}))):
                _enqueue_hailuo_poll(job.id)
            job_q.put(job.id)
    finally:
        db.close()


def worker_loop():
    while True:
        job_id = job_q.get()
        db: Session = SessionLocal()
        try:
            job = crud.get_job(db, job_id)
            if not job or job.status not in ["queued", "waiting", "running"]:
                db.close()
                job_q.task_done()
                continue

            crud.update_job(db, job.id, status="running")
            payload = json.loads(job.payload or "{}")

            if job.type == "proxy":
                assets = payload.get("assets", [])
                total = max(len(assets), 1)

                def _process_proxy(aid: str):
                    local_db: Session = SessionLocal()
                    try:
                        asset = crud.get_asset(local_db, aid)
                        if not asset:
                            return False
                        master = asset.master_path
                        proxy = master.replace("/assets/", "/assets/proxy_")
                        tasks.create_proxy(master, proxy)
                        asset.proxy_path = proxy
                        local_db.add(asset)
                        local_db.commit()
                        return True
                    finally:
                        local_db.close()

                with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(assets) or 1)) as executor:
                    completed = 0
                    for success in executor.map(_process_proxy, assets):
                        completed += 1
                        progress = int((completed / total) * 100)
                        crud.update_job(db, job.id, progress=progress)

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
                hailuo_request = payload.get("hailuo_request")
                job_set_id = job.remote_job_id or payload.get("hailuo_job_set_id")
                start_frame_path = end_frame_path = None
                cleanup_start = cleanup_end = False

                if not motion_id:
                    raise ValueError("Hailuo transition requires motion_id")

                if payload.get("asset_id"):
                    asset = crud.get_asset(db, payload["asset_id"])
                    if asset and Path(asset.master_path).exists():
                        crud.update_job(
                            db,
                            job.id,
                            status="completed",
                            progress=100,
                            result_path=asset.master_path,
                        )
                        continue

                if not job_set_id:
                    from_asset = crud.get_asset(db, from_asset_id)
                    to_asset = crud.get_asset(db, to_asset_id)
                    if not from_asset or not to_asset:
                        raise ValueError("Missing source assets for Hailuo transition")

                    if not hailuo_request:
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
                        payload["hailuo_request"] = hailuo_request

                    start_response = hailuo.start_transition(**hailuo_request)
                    job_set_id = start_response.get("job_set_id")
                    payload["hailuo_job_set_id"] = job_set_id
                    crud.update_job(
                        db,
                        job.id,
                        status="waiting",
                        payload=payload,
                        remote_job_id=job_set_id,
                        logs=json.dumps({"hailuo_request": hailuo_request, "hailuo_response": start_response}),
                    )
                else:
                    crud.update_job(db, job.id, status="waiting", payload=payload, remote_job_id=job_set_id)

                _enqueue_hailuo_poll(job.id)
                continue

            else:
                crud.update_job(db, job.id, status="failed", logs=f"unknown job type: {job.type}")

        except Exception as e:
            error_log = {"error": str(e)}
            if job:
                crud.update_job(db, job.id, status="failed", logs=json.dumps(error_log))
        finally:
            db.close()
            job_q.task_done()


def _complete_hailuo_transition(
    db: Session,
    *,
    job,
    payload: Dict,
    job_set_id: str,
    hailuo_request: Dict,
    result_url: str,
):
    output_dir = STORAGE_DIR / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{job.id}_hailuo_transition.mp4"

    if result_url:
        with httpx.Client(timeout=120) as client:
            resp = client.get(result_url)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)

    media_info = tasks.probe_media(str(output_path))

    new_asset = crud.create_asset(
        db,
        filename=output_path.name,
        master_path=str(output_path),
        project_id=job.project_id,
        duration=media_info.get("duration") if media_info else None,
        frame_rate=media_info.get("frame_rate") if media_info else None,
        metadata=media_info or None,
    )

    payload["hailuo_job_set_id"] = job_set_id
    if hailuo_request:
        payload["hailuo_request"] = hailuo_request
    payload["asset_id"] = new_asset.id

    crud.update_job(
        db,
        job.id,
        status="completed",
        progress=100,
        result_path=str(output_path),
        payload=payload,
        remote_job_id=job_set_id,
    )


def hailuo_poll_loop():
    while True:
        job_id = hailuo_poll_q.get()
        db: Session = SessionLocal()
        try:
            job = crud.get_job(db, job_id)
            if not job:
                continue

            payload = json.loads(job.payload or "{}")
            job_set_id = job.remote_job_id or payload.get("hailuo_job_set_id")
            hailuo_request = payload.get("hailuo_request") or {}

            if payload.get("asset_id"):
                asset = crud.get_asset(db, payload["asset_id"])
                if asset and Path(asset.master_path).exists():
                    crud.update_job(
                        db,
                        job.id,
                        status="completed",
                        progress=100,
                        result_path=asset.master_path,
                    )
                    continue

            if not job_set_id:
                continue

            try:
                result = hailuo.poll_existing_job(
                    job_set_id,
                    poll_interval=HAILUO_POLL_INTERVAL,
                    timeout=HAILUO_TIMEOUT,
                    max_polls=HAILUO_MAX_POLLS,
                )
            except hailuo.HailuoError as exc:
                message = str(exc).lower()
                status_to_set = "failed"
                if any(token in message for token in ("timed out", "maximum poll", "client has been closed")):
                    status_to_set = "waiting"
                crud.update_job(
                    db,
                    job.id,
                    status=status_to_set,
                    logs=json.dumps({
                        "error": str(exc),
                        "hailuo_job_set_id": job_set_id,
                        "hailuo_request": hailuo_request,
                    }),
                    remote_job_id=job_set_id,
                    payload=payload,
                )
                if status_to_set == "waiting":
                    time.sleep(max(1.0, HAILUO_POLL_INTERVAL))
                    _enqueue_hailuo_poll(job.id)
                continue

            result_url = result.get("result_url")
            if not result_url:
                raise RuntimeError("Hailuo did not return a downloadable result URL")

            _complete_hailuo_transition(
                db,
                job=job,
                payload=payload,
                job_set_id=job_set_id,
                hailuo_request=hailuo_request,
                result_url=result_url,
            )

        except Exception as exc:
            if job_id:
                crud.update_job(
                    db,
                    job_id,
                    status="failed",
                    logs=json.dumps({"error": str(exc)}),
                )
        finally:
            db.close()
            hailuo_poll_q.task_done()

def start_worker_thread():
    from .config import WORKER_THREADS
    _restore_pending_jobs()
    for i in range(WORKER_THREADS):
        t = threading.Thread(target=worker_loop, daemon=True, name=f"Worker-{i}")
        t.start()
    polling_threads = max(1, min(2, WORKER_THREADS))
    for i in range(polling_threads):
        threading.Thread(target=hailuo_poll_loop, daemon=True, name=f"HailuoPoller-{i}").start()
