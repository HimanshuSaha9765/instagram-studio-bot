import os
import logging
import subprocess
from config import MAX_FILE_SIZE_MB, TEMP_DIR

logger = logging.getLogger(__name__)

def get_file_size_mb(file_path):
    if os.path.exists(file_path):
        return os.path.getsize(file_path) / (1024 * 1024)
    return 0

def compress_video(input_path, output_path, target_size_mb=45):
    try:
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx264', '-crf', '28',
            '-preset', 'fast', '-c:a', 'aac',
            '-b:a', '128k', '-movflags', '+faststart',
            '-y', output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=180)
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        logger.error(f'Compression error: {e}')
    return None

def extract_audio(video_path, audio_path):
    try:
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'libmp3lame',
            '-q:a', '2', '-y', audio_path
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=120)
        if os.path.exists(audio_path):
            return audio_path
    except Exception as e:
        logger.error(f'Audio extraction error: {e}')
    return None

def clean_caption(caption, max_length=1000):
    if not caption:
        return None
    caption = caption.strip()
    lines = caption.split('
')
    clean_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and len(line) > 3:
            clean_lines.append(line)
        if len(clean_lines) >= 3:
            break
    result = '
'.join(clean_lines[:3])
    if len(result) > max_length:
        result = result[:max_length] + '...'
    return result if result else None

def optimize_media(file_path, media_type='video'):
    file_size = get_file_size_mb(file_path)
    if file_size <= MAX_FILE_SIZE_MB:
        return file_path, file_size
    if media_type == 'video':
        compressed_path = file_path.replace('.mp4', '_compressed.mp4')
        result = compress_video(file_path, compressed_path)
        if result:
            new_size = get_file_size_mb(result)
            if new_size <= MAX_FILE_SIZE_MB:
                os.remove(file_path)
                return result, new_size
    return None, file_size
