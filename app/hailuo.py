import time
from typing import Any, Dict, Optional

import httpx

from .config import (
    HIGGSFIELD_PLATFORM_BASE,
    HIGGSFIELD_API_KEY,
    HIGGSFIELD_API_SECRET,
    HAILUO_ENDPOINT,
    HAILUO_MODEL_ID,
)


class HailuoError(RuntimeError):
    """Raised when the Hailuo API returns an error payload."""


def _headers() -> Dict[str, str]:
    if not HIGGSFIELD_API_KEY or not HIGGSFIELD_API_SECRET:
        raise HailuoError("Missing HIGGSFIELD_API_KEY or HIGGSFIELD_API_SECRET environment variables")
    return {
        "hf-api-key": HIGGSFIELD_API_KEY,
        "hf-secret": HIGGSFIELD_API_SECRET,
        "content-type": "application/json",
    }


def start_transition(
    *,
    start_image_url: str,
    end_image_url: str,
    prompt: str,
    duration: int,
    motion_id: str,
    resolution: str,
    enhance_prompt: bool,
) -> Dict[str, Any]:
    if not motion_id:
        raise HailuoError("motion_id is required for Minimax Hailuo")

    payload: Dict[str, Any] = {
        "params": {
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "enhance_prompt": enhance_prompt,
            "motion_id": motion_id,
            "input_image": {"type": "image_url", "image_url": start_image_url},
            "input_image_end": {"type": "image_url", "image_url": end_image_url},
        },
    }

    if HAILUO_MODEL_ID:
        payload["model"] = HAILUO_MODEL_ID

    with httpx.Client(timeout=120) as client:
        resp = client.post(f"{HIGGSFIELD_PLATFORM_BASE}{HAILUO_ENDPOINT}", json=payload, headers=_headers())
        if resp.status_code >= 400:
            raise HailuoError(f"Hailuo request failed ({resp.status_code}): {resp.text}")
        data = resp.json()

    job_set_id = data.get("job_set_id") or data.get("id")
    if not job_set_id:
        raise HailuoError(f"Unexpected response from Hailuo: {data}")

    data["job_set_id"] = job_set_id
    return data


def fetch_job_set(job_set_id: str) -> Dict[str, Any]:
    with httpx.Client(timeout=60) as client:
        resp = client.get(f"{HIGGSFIELD_PLATFORM_BASE}/v1/job-sets/{job_set_id}", headers=_headers())
        resp.raise_for_status()
        return resp.json()


def extract_result(job_set: Dict[str, Any]) -> Dict[str, Optional[str]]:
    jobs = job_set.get("jobs") or []
    job_statuses = [job.get("status") for job in jobs if isinstance(job, dict)]

    if job_statuses and all((status or "").lower() in {"completed", "success", "succeeded"} for status in job_statuses):
        final_status = "completed"
    elif job_statuses and any((status or "").lower() in {"failed", "error"} for status in job_statuses):
        final_status = "failed"
    else:
        overall = (job_set.get("status") or job_set.get("overall_status") or "queued").lower()
        final_status = overall

    result_url = _extract_result_url(job_set) if final_status == "completed" else None
    return {"status": final_status, "result_url": result_url}


def _extract_result_url(job_set: Dict[str, Any]) -> Optional[str]:
    jobs = job_set.get("jobs") or []
    for job in jobs:
        for bucket in ("results", "output", "outputs"):
            container = job.get(bucket)
            if isinstance(container, dict):
                for values in container.values():
                    if isinstance(values, list):
                        for item in values:
                            if isinstance(item, dict):
                                url = item.get("url") or item.get("asset_url") or item.get("download_url")
                                if url:
                                    return url
                    elif isinstance(values, dict):
                        url = values.get("url") or values.get("asset_url") or values.get("download_url")
                        if url:
                            return url
            elif isinstance(container, list):
                for item in container:
                    if isinstance(item, dict):
                        url = item.get("url") or item.get("asset_url") or item.get("download_url")
                        if url:
                            return url
        url = job.get("result_url")
        if url:
            return url
    return job_set.get("result_url")


def poll_existing_job(
    job_set_id: str,
    *,
    poll_interval: float = 3.0,
    timeout: float = 300.0,
    max_polls: int = 0,
) -> Dict[str, Any]:
    """Poll an existing Hailuo job until completion or failure."""

    deadline: Optional[float]
    if timeout and timeout > 0:
        deadline = time.monotonic() + timeout
    else:
        deadline = None

    polls = 0
    interval = max(poll_interval or 0.0, 0.1)

    while True:
        job_set = fetch_job_set(job_set_id)
        result = extract_result(job_set)
        status = (result.get("status") or "").lower()

        if status in {"completed", "success", "succeeded"}:
            return {
                "job_set_id": job_set_id,
                "job_set": job_set,
                "result_url": result.get("result_url"),
                "status": status,
            }

        if status in {"failed", "error"}:
            raise HailuoError(f"Hailuo job failed: {job_set}")

        polls += 1
        if max_polls and polls >= max_polls:
            raise HailuoError("Maximum poll attempts exceeded while waiting for Hailuo job to complete")

        if deadline is not None and time.monotonic() >= deadline:
            raise HailuoError("Timed out waiting for Hailuo job to complete")

        time.sleep(interval)


def run_transition(
    *,
    start_image_url: str,
    end_image_url: str,
    prompt: str,
    duration: int,
    motion_id: str,
    resolution: str,
    enhance_prompt: bool,
    poll_interval: float = 3.0,
    timeout: float = 300.0,
    max_polls: int = 0,
) -> Dict[str, Any]:
    """Kick off a new Hailuo job and wait for the result synchronously."""

    start_resp = start_transition(
        start_image_url=start_image_url,
        end_image_url=end_image_url,
        prompt=prompt,
        duration=duration,
        motion_id=motion_id,
        resolution=resolution,
        enhance_prompt=enhance_prompt,
    )

    job_set_id = start_resp["job_set_id"]
    result = poll_existing_job(
        job_set_id,
        poll_interval=poll_interval,
        timeout=timeout,
        max_polls=max_polls,
    )

    result.setdefault("hailuo_response", start_resp)
    return result
