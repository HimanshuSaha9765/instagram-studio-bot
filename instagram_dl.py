import os
import logging
import base64
import yt_dlp
from instagrapi import Client
from config import COOKIE_BASE64, TEMP_DIR

logger = logging.getLogger(__name__)

def is_instagram_url(text):
    text = text.strip()
    if 'instagram.com' in text or 'instagr.am' in text:
        if '/p/' in text or '/reel/' in text or '/tv/' in text:
            return True
    return False

def get_shortcode(url):
    parts = url.split('/')
    for i, part in enumerate(parts):
        if part in ['p', 'reel', 'tv'] and i + 1 < len(parts):
            return parts[i + 1].split('?')[0]
    return None

def download_with_ytdlp(url):
    cookie_file = None
    try:
        if COOKIE_BASE64:
            cookie_file = f'{TEMP_DIR}/cookies.txt'
            cookie_content = base64.b64decode(COOKIE_BASE64).decode('utf-8')
            with open(cookie_file, 'w') as f:
                f.write(cookie_content)
        
        ydl_opts = {
            'format': 'best[filesize<50M]/best',
            'outtmpl': f'{TEMP_DIR}/%(id)s.%(ext)s',
            'quiet': False,
            'no_warnings': False
        }
        
        if cookie_file:
            ydl_opts['cookiefile'] = cookie_file
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            username = info.get('uploader_id', '') or info.get('uploader', '') or info.get('channel', '')
            caption_text = info.get('description', '')
            track_name = info.get('track', '')
            artist_name = info.get('artist', '')
            
            formatted_caption = ''
            
            if username:
                clean_username = username.replace('@', '').strip()
                formatted_caption = f'@{clean_username}'
            
            if caption_text:
                clean_text = caption_text.strip()
                if len(clean_text) > 400:
                    clean_text = clean_text[:400] + '...'
                formatted_caption += f'{clean_text}'
            
            if track_name or artist_name:
                music_info = f'🎵 {track_name}' if track_name else ''
                if artist_name:
                    music_info += f' - {artist_name}' if track_name else f'🎵 {artist_name}'
                formatted_caption += music_info
            
            media_type = 'video'
            
            if cookie_file and os.path.exists(cookie_file):
                os.remove(cookie_file)
            
            return {
                'success': True,
                'files': [filename],
                'media_type': media_type,
                'caption': formatted_caption.strip(),
                'username': username
            }
    except Exception as e:
        logger.error(f'yt-dlp error: {e}')
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)
        return None

def download_with_instagrapi(url):
    try:
        cl = Client()
        cl.delay_range = [1, 3]
        
        shortcode = get_shortcode(url)
        if not shortcode:
            return None
        
        media_pk = cl.media_pk_from_code(shortcode)
        media_info = cl.media_info(media_pk)
        
        files = []
        username = media_info.user.username if media_info.user else ''
        caption_text = media_info.caption_text if media_info.caption_text else ''
        
        formatted_caption = ''
        if username:
            formatted_caption = f'@{username}'
        if caption_text:
            clean_text = caption_text.strip()
            if len(clean_text) > 400:
                clean_text = clean_text[:400] + '...'
            formatted_caption += clean_text
        
        if media_info.media_type == 1:
            photo_path = cl.photo_download(media_pk, folder=TEMP_DIR)
            if os.path.exists(photo_path):
                files.append(photo_path)
        elif media_info.media_type == 2:
            video_path = cl.video_download(media_pk, folder=TEMP_DIR)
            if os.path.exists(video_path):
                files.append(video_path)
        elif media_info.media_type == 8:
            for resource in media_info.resources:
                if resource.media_type == 1:
                    photo_path = cl.photo_download_by_url(resource.thumbnail_url, folder=TEMP_DIR)
                    if os.path.exists(photo_path):
                        files.append(photo_path)
                elif resource.media_type == 2:
                    video_path = cl.video_download_by_url(resource.video_url, folder=TEMP_DIR)
                    if os.path.exists(video_path):
                        files.append(video_path)
        
        is_carousel = media_info.media_type == 8
        media_type = 'video' if media_info.media_type == 2 else 'photo'
        
        return {
            'success': True,
            'files': files,
            'media_type': media_type,
            'caption': formatted_caption.strip(),
            'is_carousel': is_carousel
        }
    except Exception as e:
        logger.error(f'Instagrapi error: {e}')
        return None

def download_instagram(url):
    result = download_with_ytdlp(url)
    if result and result['success']:
        return result
    
    result = download_with_instagrapi(url)
    if result and result['success']:
        return result
    
    return None
