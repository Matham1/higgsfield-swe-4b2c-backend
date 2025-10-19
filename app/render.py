import os
import subprocess
from typing import Dict, List, Any, Tuple
import logging
from . import crud
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_asset_path(db: Session, asset_id: str) -> str:
    asset = crud.get_asset(db, asset_id)
    if not asset:
        raise ValueError(f"Asset with id {asset_id} not found")
    return asset.master_path

def build_ffmpeg_command(db: Session, timeline: Dict[str, Any], job_id: str) -> tuple[List[str], str]:
    """
    Builds an ffmpeg command from a timeline JSON object.
    """
    output_settings = timeline.get("output_settings", {})
    output_filename = output_settings.get("output_filename", f"{job_id}.mp4")
    output_resolution = output_settings.get("resolution", "1920x1080")
    output_framerate = str(output_settings.get("framerate", "30"))
    video_codec = output_settings.get("video_codec", "libx264")
    audio_codec = output_settings.get("audio_codec", "aac")
    bitrate = output_settings.get("bitrate")

    tracks = timeline.get("tracks", [])
    video_clips = []
    for track in tracks:
        if track.get("type") == "video":
            video_clips.extend(track.get("clips", []))

    if not video_clips:
        raise ValueError("No video clips found in the timeline.")

    # For this implementation, we'll assume a simple concatenation.
    # A real-world scenario would require complex filtergraphs for transitions and effects.
    
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate trimmed clips with proper in/out points
    filter_complex = []
    inputs = []
    has_audio = False

    for i, clip in enumerate(video_clips):
        asset_path = get_asset_path(db, clip['asset_id'])
        # Check if the input file has audio
        probe_cmd = ["ffprobe", "-i", asset_path, "-show_streams", "-select_streams", "a", "-v", "0", "-f", "null", "-"]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.stdout or result.stderr:
            has_audio = True

        inputs.extend(['-i', asset_path])
        # Calculate clip duration from source points
        clip_duration = clip['source_out'] - clip['source_in']
        
        # Add scaling, trim filter, and setpts to correct timestamps for each clip
        filter_complex.append(f'[{i}:v]scale={output_resolution},trim=start={clip["source_in"]}:duration={clip_duration},setpts=PTS-STARTPTS[v{i}]')
        if has_audio:
            filter_complex.append(f'[{i}:a]atrim=start={clip["source_in"]}:duration={clip_duration},asetpts=PTS-STARTPTS[a{i}]')

    # Concatenate all processed clips
    video_chain = ''.join(f'[v{i}]' for i in range(len(video_clips)))
    filter_complex.append(f'{video_chain}concat=n={len(video_clips)}:v=1:a=0[vout]')
    
    if has_audio:
        audio_chain = ''.join(f'[a{i}]' for i in range(len(video_clips)))
        filter_complex.append(f'{audio_chain}concat=n={len(video_clips)}:v=0:a=1[aout]')
    
    # Scaling is now done per-clip, so remove the final scaling filter
    # filter_complex.append(f'[vcont]scale={output_resolution}[vout]')

    output_dir = "storage/renders"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)

    ffmpeg_command = ["ffmpeg"]
    ffmpeg_command.extend(inputs)
    
    # Add filter complex
    filter_str = ';'.join(filter_complex)
    ffmpeg_command.extend([
        "-filter_complex", filter_str,
        "-map", "[vout]",
    ])
    
    if has_audio:
        ffmpeg_command.extend([
            "-map", "[aout]",
            "-c:a", audio_codec,
        ])
    
    ffmpeg_command.extend([
        "-r", output_framerate,
        "-c:v", video_codec,
    ])
    
    if bitrate:
        ffmpeg_command.extend(["-b:v", bitrate])
    
    ffmpeg_command.extend(["-y", output_path])

    return ffmpeg_command, output_path

def run_ffmpeg_render(command: List[str], job_id: str):
    """Executes the ffmpeg command and logs the output."""
    logger.info(f"Starting ffmpeg render for job {job_id}: {' '.join(command)}")
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    logs = []
    while True:
        line = process.stdout.readline()
        if not line:
            break
        logger.info(line.strip())
        logs.append(line.strip())

    process.wait()

    if process.returncode != 0:
        logger.error(f"ffmpeg render for job {job_id} failed with return code {process.returncode}")
        raise RuntimeError(f"ffmpeg failed: {' '.join(logs)}")

    logger.info(f"ffmpeg render for job {job_id} completed successfully.")
    return "".join(logs)
