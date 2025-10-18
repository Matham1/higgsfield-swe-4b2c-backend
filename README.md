install ffmpeg and Python dependencies:
```
# on macOS (brew) or apt-get on Ubuntu
brew install ffmpeg
pip install -r requirements.txt
```

run server:
```
uvicorn app.main:app --reload
```

upload a file:
```
curl -F "file=@/path/to/video.mp4" http://localhost:8000/upload/
```

start render (example payload uses timeline with asset IDs returned by upload):
```
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

```
poll job status: GET /renders/{job_id}; download result from result_path.
