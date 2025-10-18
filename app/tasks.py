import subprocess
from pathlib import Path
from .config import FFMPEG_BIN
from typing import List

def create_proxy(master_path: str, proxy_path: str, height: int = 480):
    Path(proxy_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG_BIN, "-y", "-i", master_path,
        "-vf", f"scale=-2:{height}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        proxy_path
    ]
    subprocess.check_call(cmd)
    return proxy_path

def concat_files_reencode(input_paths: List[str], out_path: str):
    """Robust concat: re-encode everything into a single file using filter_complex concat."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    # Build input args
    cmd = [FFMPEG_BIN, "-y"]
    for p in input_paths:
        cmd += ["-i", p]
    n = len(input_paths)
    # Build concat filter
    # Example filter: [0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]
    vf = ""
    for i in range(n):
        vf += f"[{i}:v:0][{i}:a:0]"
    vf += f"concat=n={n}:v=1:a=1[outv][outa]"
    cmd += ["-filter_complex", vf, "-map", "[outv]", "-map", "[outa]", "-c:v", "libx264", "-preset", "medium", "-crf", "22", out_path]
    subprocess.check_call(cmd)
    return out_path


def _extract_frame(video_path: str, frame_path: str, *, from_end: bool = False, offset: float = 0.04):
    """Extract a single frame from the given video.

    When ``from_end`` is True, grabs a frame within ``offset`` seconds of the end; otherwise uses
    ``offset`` seconds from the start. ``offset`` defaults to 40ms to keep things snappy while still
    generating a visually representative frame.
    """

    Path(frame_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG_BIN, "-y"]
    if from_end:
        cmd += ["-sseof", f"-{abs(offset)}"]
    else:
        cmd += ["-ss", f"{max(offset, 0):.3f}"]

    cmd += ["-i", video_path, "-frames:v", "1", "-q:v", "2", frame_path]
    subprocess.check_call(cmd)
    return frame_path


def extract_first_frame(video_path: str, frame_path: str, offset: float = 0.0):
    return _extract_frame(video_path, frame_path, from_end=False, offset=offset)


def extract_last_frame(video_path: str, frame_path: str, offset: float = 0.08):
    return _extract_frame(video_path, frame_path, from_end=True, offset=offset)
