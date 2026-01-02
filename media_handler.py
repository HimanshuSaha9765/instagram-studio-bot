import os
import logging
import subprocess
from config import MAX_FILE_SIZE_MB, TEMP_DIR, COMPRESSION_QUALITY

logger = logging.getLogger(__name__)

def get_file_size_mb(file_path):
    if os.path.exists(file_path):
        return os.path.getsize(file_path) / (1024 * 1024)
    return 0

def compress_video(input_path, output_path, crf=23):
    try:
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx264', '-crf', str(crf),
            '-preset', 'medium', '-c:a', 'aac',
            '-b:a', '128k', '-movflags', '+faststart',
            '-y', output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=180)
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        logger.error(f'Compression error: {e}')
    return None

def compress_image(input_path, output_path, quality=85):
    try:
        from PIL import Image
        img = Image.open(input_path)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(output_path, 'JPEG', quality=quality, optimize=True)
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        logger.error(f'Image compression error: {e}')
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

def optimize_media(file_path, media_type='video'):
    file_size = get_file_size_mb(file_path)
    
    if media_type == 'video':
        compressed_path = file_path.replace('.mp4', '_compressed.mp4')
        
        if file_size > MAX_FILE_SIZE_MB:
            crf = 28
        elif file_size > 30:
            crf = 25
        else:
            crf = COMPRESSION_QUALITY
        
        result = compress_video(file_path, compressed_path, crf)
        
        if result:
            new_size = get_file_size_mb(result)
            if new_size <= MAX_FILE_SIZE_MB:
                os.remove(file_path)
                return result, new_size
            elif new_size > MAX_FILE_SIZE_MB and crf < 32:
                os.remove(result)
                result = compress_video(file_path, compressed_path, 32)
                if result:
                    final_size = get_file_size_mb(result)
                    if final_size <= MAX_FILE_SIZE_MB:
                        os.remove(file_path)
                        return result, final_size
                    os.remove(result)
        
        return None, file_size
    
    elif media_type == 'photo':
        if file_size <= MAX_FILE_SIZE_MB:
            return file_path, file_size
        
        compressed_path = file_path.replace('.jpg', '_compressed.jpg')
        quality = 85 if file_size < 10 else 75
        
        result = compress_image(file_path, compressed_path, quality)
        if result:
            new_size = get_file_size_mb(result)
            if new_size <= MAX_FILE_SIZE_MB:
                os.remove(file_path)
                return result, new_size
        
        return None, file_size
    
    return file_path, file_size
