import os
import logging
from flask import Flask, request
from config import TOKEN
from instagram_dl import is_instagram_url, download_instagram
from media_handler import optimize_media, extract_audio, get_file_size_mb
from telegram_sender import send_message, send_video, send_photo, send_audio, send_video_with_button, answer_callback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

video_cache = {}

def cleanup_user_cache(chat_id):
    to_delete = []
    for video_id, (path, owner_chat_id) in video_cache.items():
        if owner_chat_id == chat_id:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f'Cleaned up old video: {video_id}')
            to_delete.append(video_id)
    for video_id in to_delete:
        del video_cache[video_id]

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
        if 'callback_query' in data:
            handle_callback_query(data['callback_query'])
            return 'ok', 200
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            
            if 'text' in message:
                text = message['text']
                
                if text == '/start':
                    msg = 'Hello AXIOM Instagram Studio Bot. \nSend Instagram reel link. \nFeatures: \nSmart quality, \nAudio extraction, \nAuto cleanup.'
                    send_message(chat_id, msg)
                
                elif is_instagram_url(text):
                    cleanup_user_cache(chat_id)
                    
                    send_message(chat_id, 'Downloading from Instagram...')
                    
                    result = download_instagram(text)
                    
                    if not result:
                        send_message(chat_id, 'Download failed. Try another link or wait if rate-limited.')
                        return 'ok', 200
                    
                    files = result.get('files', [])
                    caption = result.get('caption', '')
                    is_carousel = result.get('is_carousel', False)
                    
                    if not files:
                        send_message(chat_id, 'No media found.')
                        return 'ok', 200
                    
                    send_message(chat_id, f'Processing {len(files)} file(s)...')
                    
                    for idx, file_path in enumerate(files):
                        if not os.path.exists(file_path):
                            continue
                        
                        ext = file_path.split('.')[-1].lower()
                        is_video = ext in ['mp4', 'mov', 'webm']
                        
                        if is_video:
                            optimized, size = optimize_media(file_path, 'video')
                            
                            if not optimized:
                                send_message(chat_id, f'Video {idx+1} too large ({size:.1f}MB).')
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                continue
                            
                            video_id = os.path.basename(optimized).replace('.mp4', '').replace('_compressed', '')
                            video_cache[video_id] = (optimized, chat_id)
                            
                            item_caption = caption if idx == 0 else f'Part {idx+1}'
                            send_video_with_button(chat_id, optimized, item_caption, video_id)
                        else:
                            send_photo(chat_id, file_path, caption if idx == 0 else None)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                    
                    send_message(chat_id, 'Done! Use buttons below video.')
                
                else:
                    send_message(chat_id, 'Send me an Instagram reel link.')
        
        return 'ok', 200
    except Exception as e:
        logger.error(f'Webhook error: {e}')
        return 'error', 500

def handle_callback_query(callback_query):
    callback_id = callback_query['id']
    chat_id = callback_query['message']['chat']['id']
    data = callback_query['data']
    
    if data.startswith('audio:'):
        video_id = data.split(':', 1)[1]
        
        answer_callback(callback_id, 'Extracting audio...')
        send_message(chat_id, 'Extracting audio, please wait...')
        
        cached_data = video_cache.get(video_id)
        
        if not cached_data:
            send_message(chat_id, 'Video expired. Please resend the link.')
            return
        
        video_path, owner_chat_id = cached_data
        
        if not os.path.exists(video_path):
            send_message(chat_id, 'Video file not found. Please resend the link.')
            del video_cache[video_id]
            return
        
        audio_path = video_path.replace('.mp4', '_audio.mp3')
        result = extract_audio(video_path, audio_path)
        
        if result and os.path.exists(audio_path):
            send_audio(chat_id, audio_path, f'{video_id} Audio')
            os.remove(audio_path)
        else:
            send_message(chat_id, 'Audio extraction failed.')
        
        if os.path.exists(video_path):
            os.remove(video_path)
        del video_cache[video_id]
    
    elif data.startswith('noaudio:'):
        video_id = data.split(':', 1)[1]
        
        answer_callback(callback_id, 'Video deleted from server')
        
        cached_data = video_cache.get(video_id)
        
        if cached_data:
            video_path, owner_chat_id = cached_data
            if os.path.exists(video_path):
                os.remove(video_path)
                logger.info(f'User declined audio, deleted: {video_id}')
            del video_cache[video_id]
            send_message(chat_id, 'Video deleted from server.')

@app.route('/health', methods=['GET'])
def health():
    return 'AXIOM System Active', 200
