# Higgsfield Backend

install ffmpeg and Python dependencies:

```bash
# on macOS (brew) or apt-get on Ubuntu
brew install ffmpeg
pip install -r requirements.txt
```

run server:

```bash
uvicorn app.main:app --reload
```

## Environment

Create a `.env` file in the repository root (example values below) and load it when the server starts automatically:

```bash
HIGGSFIELD_API_KEY=your_hf_api_key
HIGGSFIELD_API_SECRET=your_hf_secret
# base URL that Hailuo will use to pull extracted frames back (should be externally reachable in production)
PUBLIC_BASE_URL=http://localhost:8000
# optional polling/timeout tuning for Minimax Hailuo jobs (seconds)
# HAILUO_TIMEOUT=600
# HAILUO_POLL_INTERVAL=5
# HAILUO_MAX_POLLS=0  # optional hard cap on poll attempts (0 = unlimited until timeout)
# Optional: configure remote storage for extracted frames
# R2_ACCESS_KEY_ID=...
# R2_SECRET_ACCESS_KEY=...
# R2_BUCKET_NAME=...
# R2_ACCOUNT_ID=...
# R2_PUBLIC_DOMAIN=https://your-bucket.r2.cloudflarestorage.com
# optional overrides:
# HIGGSFIELD_PLATFORM_BASE=https://platform.higgsfield.ai
# Optional: set HAILUO_MODEL_ID if the endpoint requires an explicit model identifier
# HAILUO_MODEL_ID=minimax-hailuo-02
```

## Key Endpoints

- `POST /upload/` — upload media assets; saves them to `storage/assets/` and enqueues proxy generation.
- `GET /upload/{asset_id}` — fetch metadata for an uploaded/ generated asset.
- `GET /transitions/hailuo/motions` — returns the cached Minimax Hailuo 02 motion catalogue (id, name, description, etc.).
- `POST /transitions/hailuo` — queue a Minimax Hailuo transition job using the last frame of one asset and the first frame of another. **`motion_id` is required** and must come from the motion catalogue above. Payload shape:

  ```json
  {
    "project_id": "optional-project",
    "from_asset_id": "assetA",
    "to_asset_id": "assetB",
    "prompt": "Seamless cinematic bridge",
    "motion_id": "ea035f68-b350-40f1-b7f4-7dff999fdd67",
    "duration": 2,
    "resolution": "768",
    "enhance_prompt": true
  }
  ```

  Response returns `{ "job_id": "job_xxx" }`; poll `/jobs/{job_id}` until `status` is `completed`, then inspect `payload.asset_id` for the generated transition asset. Static files are served from `/storage/...` for direct download.

upload a file:

```bash
curl -F "file=@/path/to/video.mp4" http://localhost:8000/upload/
```

start render (example payload uses timeline with asset IDs returned by upload):

```bash
POST /renders/ with JSON:
{
  "project_id": null,
  "type": "render",
  "payload": {
     "timeline": [
        {"asset_id": "abcdef..."},
        {"asset_id": "123456..."}
     ]
  }
}

```bash
poll job status: GET /renders/{job_id}; download result from result_path.
