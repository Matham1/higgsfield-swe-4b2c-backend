import threading, queue, time, json
from sqlalchemy.orm import Session
from .db import SessionLocal
from . import crud, tasks, higgsfield
from typing import Dict

job_q = queue.Queue()

def enqueue_job(job_id: str):
    job_q.put(job_id)

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
                timeline = payload.get("timeline", [])
                paths = []
                for item in timeline:
                    if "asset_id" in item:
                        asset = crud.get_asset(db, item["asset_id"])
                        if not asset: continue
                        p = asset.proxy_path if item.get("use_proxy") and asset.proxy_path else asset.master_path
                        paths.append(p)
                    elif "path" in item:
                        paths.append(item["path"])
                out = f"./storage/renders/{job.id}.mp4"
                tasks.concat_files_reencode(paths, out)
                crud.update_job(db, job.id, status="completed", progress=100, result_path=out)
            
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

            else:
                crud.update_job(db, job.id, status="failed", logs=f"unknown job type: {job.type}")

        except Exception as e:
            crud.update_job(db, job_id, status="failed", logs=str(e))
        finally:
            db.close()
            job_q.task_done()
        
        time.sleep(0.1)

def start_worker_thread():
    from .config import WORKER_THREADS
    for i in range(WORKER_THREADS):
        t = threading.Thread(target=worker_loop, daemon=True, name=f"Worker-{i}")
        t.start()
