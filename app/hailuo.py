import asyncio
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


async def _start_transition(
    client: httpx.AsyncClient,
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

    resp = await client.post(f"{HIGGSFIELD_PLATFORM_BASE}{HAILUO_ENDPOINT}", json=payload, headers=_headers())
    if resp.status_code >= 400:
        raise HailuoError(
            f"Hailuo request failed ({resp.status_code}): {resp.text}"
        )
    data = resp.json()
    job_set_id = data.get("job_set_id") or data.get("id")
    if not job_set_id:
        raise HailuoError(f"Unexpected response from Hailuo: {data}")
    data["job_set_id"] = job_set_id
    return data


async def _fetch_job_set(client: httpx.AsyncClient, job_set_id: str) -> Dict[str, Any]:
    resp = await client.get(
        f"{HIGGSFIELD_PLATFORM_BASE}/v1/job-sets/{job_set_id}",
        headers=_headers(),
    )
    resp.raise_for_status()
    return resp.json()


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
        # Some APIs bubble up URLs directly under job
        url = job.get("result_url")
        if url:
            return url
    # Try top-level convenience field
    return job_set.get("result_url")


async def generate_transition(
    *,
    start_image_url: str,
    end_image_url: str,
    prompt: str,
    duration: int,
    motion_id: str,
    resolution: str = "768",
    enhance_prompt: bool = True,
    poll_interval: float = 2.5,
    timeout: float = 180.0,
) -> Dict[str, Any]:
    """Create a Hailuo transition and wait for completion.

    Returns a dict with keys: job_set_id, job_set (final payload), result_url (if available).
    """

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, read=timeout)) as client:
        start_resp = await _start_transition(
            client,
            start_image_url=start_image_url,
            end_image_url=end_image_url,
            prompt=prompt,
            duration=duration,
            motion_id=motion_id,
            resolution=resolution,
            enhance_prompt=enhance_prompt,
        )

        job_set_id = start_resp["job_set_id"]
        elapsed = 0.0

        while True:
            job_set = await _fetch_job_set(client, job_set_id)
            status = job_set.get("status") or job_set.get("overall_status")
            if status in {"completed", "succeeded", "success"}:
                return {
                    "job_set_id": job_set_id,
                    "job_set": job_set,
                    "result_url": _extract_result_url(job_set),
                }
            if status in {"failed", "error"}:
                raise HailuoError(f"Hailuo job failed: {job_set}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            if elapsed >= timeout:
                raise HailuoError("Timed out waiting for Hailuo job to complete")


def run_transition(**kwargs) -> Dict[str, Any]:
    """Synchronous helper for worker thread."""
    return asyncio.run(generate_transition(**kwargs))
