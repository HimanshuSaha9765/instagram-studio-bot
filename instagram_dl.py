import os
import logging
import base64
import yt_dlp
import instaloader
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
            
            username = info.get('uploader', '') or info.get('channel', '') or info.get('uploader_id', '')
            caption_text = info.get('description', '')
            track_name = info.get('track', '')
            artist_name = info.get('artist', '')
            
            formatted_caption = ''
            
            if username:
                formatted_caption = f'@{username}'
            
            if caption_text:
                clean_text = caption_text.strip()
                if len(clean_text) > 500:
                    clean_text = clean_text[:500] + '...'
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

def download_with_instaloader(url):
    try:
        L = instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            dirname_pattern=TEMP_DIR,
            filename_pattern='{shortcode}'
        )
        
        shortcode = get_shortcode(url)
        if not shortcode:
            return None
        
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        files = []
        caption = post.caption if post.caption else ''
        username = post.owner_username if hasattr(post, 'owner_username') else '' 
        
        formatted_caption = ''
        if username:
            formatted_caption = f'@{username}'
        if caption:
            clean_text = caption.strip()
            if len(clean_text) > 500:
                clean_text = clean_text[:500] + '...'
            formatted_caption += clean_text
        
        if post.typename == 'GraphSidecar':
            for i, node in enumerate(post.get_sidecar_nodes()):
                if node.is_video:
                    video_url = node.video_url
                    filename = f'{TEMP_DIR}/{shortcode}_{i}.mp4'
                    L.download_pic(filename, video_url, post.date_utc)
                    if os.path.exists(filename):
                        files.append(filename)
                else:
                    image_url = node.display_url
                    filename = f'{TEMP_DIR}/{shortcode}_{i}.jpg'
                    L.download_pic(filename, image_url, post.date_utc)
                    if os.path.exists(filename):
                        files.append(filename)
        elif post.is_video:
            filename = f'{TEMP_DIR}/{shortcode}.mp4'
            L.download_pic(filename, post.video_url, post.date_utc)
            if os.path.exists(filename):
                files.append(filename)
        else:
            filename = f'{TEMP_DIR}/{shortcode}.jpg'
            L.download_pic(filename, post.url, post.date_utc)
            if os.path.exists(filename):
                files.append(filename)
        
        media_type = 'video' if post.is_video else 'photo'
        
        return {
            'success': True,
            'files': files,
            'media_type': media_type,
            'caption': formatted_caption.strip(),
            'is_carousel': post.typename == 'GraphSidecar'
        }
    except Exception as e:
        logger.error(f'Instaloader error: {e}')
        return None

def download_instagram(url):
    result = download_with_ytdlp(url)
    if result and result['success']:
        return result
    
    result = download_with_instaloader(url)
    if result and result['success']:
        return result
    
    return None
