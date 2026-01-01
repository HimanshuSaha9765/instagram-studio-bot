import os
import logging
from flask import Flask, request
from config import TOKEN
from instagram_dl import is_instagram_url, download_instagram
from media_handler import optimize_media, clean_caption, extract_audio, get_file_size_mb
from telegram_sender import send_message, send_video, send_photo, send_audio, create_inline_keyboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
        if 'callback_query' in data:
            handle_callback(data['callback_query'])
            return 'ok', 200
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            
            if 'text' in message:
                text = message['text']
                
                if text == '/start':
                    welcome_text = 'Hello! AXIOM Instagram Studio Bot.\n Send Instagram link (reel/post/carousel) \n Features: \n - Smart quality optimization \n- Photo & video support \n- Audio extraction \n- Auto compression'
                    send_message(chat_id, welcome_text)
                
                elif is_instagram_url(text):
                    send_message(chat_id, 'Downloading from Instagram...')
                    
                    result = download_instagram(text)
                    
                    if not result:
                        send_message(chat_id, 'Download failed. Try another link.')
                        return 'ok', 200
                    
                    files = result.get('files', [])
                    caption = clean_caption(result.get('caption', ''))
                    is_carousel = result.get('is_carousel', False)
                    
                    if not files:
                        send_message(chat_id, 'No media found.')
                        return 'ok', 200
                    
                    send_message(chat_id, f'Processing {len(files)} media file(s)...')
                    
                    for file_path in files:
                        if not os.path.exists(file_path):
                            continue
                        
                        ext = file_path.split('.')[-1].lower()
                        is_video = ext in ['mp4', 'mov', 'webm']
                        
                        if is_video:
                            optimized, size = optimize_media(file_path, 'video')
                            if not optimized:
                                send_message(chat_id, f'Video too large ({size:.1f}MB) after compression.')
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                continue
                            
                            send_video(chat_id, optimized, caption)
                            
                            audio_path = optimized.replace('.mp4', '_audio.mp3')
                            audio_result = extract_audio(optimized, audio_path)
                            if audio_result and os.path.exists(audio_path):
                                send_message(chat_id, 'Audio extracted. Sending...')
                                send_audio(chat_id, audio_path, 'Instagram Audio')
                                os.remove(audio_path)
                            
                            if os.path.exists(optimized):
                                os.remove(optimized)
                        else:
                            send_photo(chat_id, file_path, caption)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                    
                    send_message(chat_id, 'Done!')
                
                else:
                    send_message(chat_id, 'Send me an Instagram link (reel/post/carousel).')
        
        return 'ok', 200
    except Exception as e:
        logger.error(f'Webhook error: {e}')
        return 'error', 500

def handle_callback(callback_query):
    chat_id = callback_query['message']['chat']['id']
    data = callback_query['data']
    
    if data.startswith('audio:'):
        audio_file = data.split(':', 1)[1]
        audio_path = f'/tmp/{audio_file}'
        
        if os.path.exists(audio_path):
            send_audio(chat_id, audio_path, 'Instagram Audio')
            os.remove(audio_path)
        else:
            send_message(chat_id, 'Audio file expired.')

@app.route('/health', methods=['GET'])
def health():
    return 'AXIOM System Active', 200
