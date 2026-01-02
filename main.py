import os
import logging
import time
import threading
from flask import Flask, request
from config import TOKEN, AUDIO_CACHE_TIMEOUT
from instagram_dl import is_instagram_url, download_instagram
from media_handler import optimize_media, extract_audio, get_file_size_mb
from telegram_sender import (send_message, send_video, send_photo, send_audio, send_video_with_button, answer_callback, delete_message)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

audio_cache = {}
user_processing = {}

def cleanup_audio_cache(audio_id):
    time.sleep(AUDIO_CACHE_TIMEOUT)
    if audio_id in audio_cache:
        audio_path, chat_id = audio_cache[audio_id]
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f'Auto-deleted audio after timeout: {audio_id}')
        del audio_cache[audio_id]

def cleanup_user_audio(chat_id):
    to_delete = []
    for audio_id, (path, owner_chat_id) in audio_cache.items():
        if owner_chat_id == chat_id:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f'Cleaned up user audio: {audio_id}')
            to_delete.append(audio_id)
    for audio_id in to_delete:
        del audio_cache[audio_id]

def delete_status_messages(chat_id, message_ids):
    for msg_id in message_ids:
        if msg_id:
            delete_message(chat_id, msg_id)

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
            
            if user_processing.get(chat_id):
                return 'ok', 200
            
            if 'text' in message:
                text = message['text']
                
                if text == '/start':
                    msg = 'Hello AXIOM Instagram Studio Bot. \nSend Instagram link (reel/post/carousel).\nFeatures:\nSmart compression\nAudio extraction\nAuto cleanup.'
                    send_message(chat_id, msg)
                
                elif is_instagram_url(text):
                    user_processing[chat_id] = True
                    cleanup_user_audio(chat_id)
                    
                    status_messages = []
                    
                    msg1 = send_message(chat_id, 'Downloading from Instagram...')
                    if msg1 and 'result' in msg1:
                        status_messages.append(msg1['result']['message_id'])
                    
                    result = download_instagram(text)
                    
                    if not result:
                        delete_status_messages(chat_id, status_messages)
                        send_message(chat_id, 'Download failed. Instagram may be blocking requests. Wait 5-10 minutes and try again.')
                        user_processing[chat_id] = False
                        return 'ok', 200
                    
                    files = result.get('files', [])
                    caption = result.get('caption', '')
                    is_carousel = result.get('is_carousel', False)
                    
                    if not files:
                        delete_status_messages(chat_id, status_messages)
                        send_message(chat_id, 'No media found.')
                        user_processing[chat_id] = False
                        return 'ok', 200
                    
                    msg2 = send_message(chat_id, f'Processing {len(files)} file(s)...')
                    if msg2 and 'result' in msg2:
                        status_messages.append(msg2['result']['message_id'])
                    
                    start_time = time.time()
                    slow_msg_sent = False
                    
                    for idx, file_path in enumerate(files):
                        if time.time() - start_time > 30 and not slow_msg_sent:
                            msg3 = send_message(chat_id, 'Please wait, processing is taking time...')
                            if msg3 and 'result' in msg3:
                                status_messages.append(msg3['result']['message_id'])
                            slow_msg_sent = True
                        
                        if not os.path.exists(file_path):
                            continue
                        
                        ext = file_path.split('.')[-1].lower()
                        is_video = ext in ['mp4', 'mov', 'webm']
                        
                        if is_video:
                            optimized, size = optimize_media(file_path, 'video')
                            
                            if not optimized:
                                send_message(chat_id, f'Video {idx+1} too large even after compression.')
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                continue
                            
                            video_id = os.path.basename(optimized).replace('.mp4', '').replace('_compressed', '')
                            
                            audio_path = optimized.replace('.mp4', '_audio_temp.mp3')
                            audio_result = extract_audio(optimized, audio_path)
                            
                            if audio_result and os.path.exists(audio_path):
                                audio_cache[video_id] = (audio_path, chat_id)
                                threading.Thread(target=cleanup_audio_cache, args=(video_id,), daemon=True).start()
                            
                            item_caption = caption if idx == 0 else f'Part {idx+1}'
                            send_video_with_button(chat_id, optimized, item_caption, video_id)
                            
                            if os.path.exists(optimized):
                                os.remove(optimized)
                        else:
                            optimized, size = optimize_media(file_path, 'photo')
                            
                            if not optimized:
                                send_message(chat_id, f'Photo {idx+1} too large.')
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                continue
                            
                            send_photo(chat_id, optimized, caption if idx == 0 else None)
                            if os.path.exists(optimized):
                                os.remove(optimized)
                    
                    delete_status_messages(chat_id, status_messages)
                    send_message(chat_id, 'Done! Click audio button within 2 minutes if needed.')
                    user_processing[chat_id] = False
                
                else:
                    send_message(chat_id, 'Send me an Instagram link (reel/post/carousel).')
        
        return 'ok', 200
    except Exception as e:
        logger.error(f'Webhook error: {e}')
        if 'chat_id' in locals():
            user_processing[chat_id] = False
        return 'error', 500

def handle_callback_query(callback_query):
    callback_id = callback_query['id']
    chat_id = callback_query['message']['chat']['id']
    data = callback_query['data']
    
    if data.startswith('audio:'):
        video_id = data.split(':', 1)[1]
        
        answer_callback(callback_id, 'Preparing audio...')
        
        status_messages = []
        msg1 = send_message(chat_id, 'Extracting audio, please wait...')
        if msg1 and 'result' in msg1:
            status_messages.append(msg1['result']['message_id'])
        
        cached_data = audio_cache.get(video_id)
        
        if not cached_data:
            delete_status_messages(chat_id, status_messages)
            send_message(chat_id, 'Audio expired (2 min timeout). Please resend link.')
            return
        
        audio_path, owner_chat_id = cached_data
        
        if not os.path.exists(audio_path):
            delete_status_messages(chat_id, status_messages)
            send_message(chat_id, 'Audio file not found. Please resend link.')
            del audio_cache[video_id]
            return
        
        send_audio(chat_id, audio_path, f'{video_id} Audio')
        
        if os.path.exists(audio_path):
            os.remove(audio_path)
        del audio_cache[video_id]
        
        delete_status_messages(chat_id, status_messages)
    
    elif data.startswith('noaudio:'):
        video_id = data.split(':', 1)[1]
        
        answer_callback(callback_id, 'Deleted from server')
        
        cached_data = audio_cache.get(video_id)
        
        if cached_data:
            audio_path, owner_chat_id = cached_data
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f'User declined audio: {video_id}')
            del audio_cache[video_id]

@app.route('/health', methods=['GET'])
def health():
    return 'AXIOM System Active', 200
