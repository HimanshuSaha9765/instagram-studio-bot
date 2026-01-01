import os
import logging
import requests
from flask import Flask, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_API = f'https://api.telegram.org/bot{TOKEN}'

app = Flask(__name__)

def send_telegram_message(chat_id, text):
    payload = {'chat_id': chat_id, 'text': text}
    try:
        response = requests.post(f'{TELEGRAM_API}/sendMessage', json=payload)
        return response.json()
    except Exception as e:
        logger.error(f'Send message error: {e}')
        return None

def send_telegram_video(chat_id, video_path):
    try:
        with open(video_path, 'rb') as video:
            files = {'video': video}
            data = {'chat_id': chat_id}
            response = requests.post(f'{TELEGRAM_API}/sendVideo', data=data, files=files)
        return response.json()
    except Exception as e:
        logger.error(f'Send video error: {e}')
        return None

def is_instagram_url(text):
    text = text.strip()
    if 'instagram.com' in text or 'instagr.am' in text:
        if '/p/' in text or '/reel/' in text or '/tv/' in text:
            return True
    return False

def download_instagram(url):
    import yt_dlp
    cookies = os.environ.get('INSTAGRAM_COOKIES', '')
    cookie_file = None
    if cookies:
        cookie_file = '/tmp/cookies.txt'
        with open(cookie_file, 'w') as f:
            f.write(cookies)
    ydl_opts = {
        'format': 'best',
        'outtmpl': '/tmp/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True
    }
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if cookie_file and os.path.exists(cookie_file):
                os.remove(cookie_file)
            return filename
    except Exception as e:
        logger.error(f'Download error: {e}')
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            if 'text' in message:
                text = message['text']
                if text == '/start':
                    send_telegram_message(chat_id, 'Hello AXIOM is online. Send me an Instagram link.')
                elif is_instagram_url(text):
                    send_telegram_message(chat_id, 'Downloading from Instagram...')
                    video_path = download_instagram(text)
                    if video_path:
                        send_telegram_message(chat_id, 'Sending video...')
                        send_telegram_video(chat_id, video_path)
                        if os.path.exists(video_path):
                            os.remove(video_path)
                    else:
                        send_telegram_message(chat_id, 'Failed to download. Try another link.')
                else:
                    send_telegram_message(chat_id, 'AXIOM received your message. Send Instagram link to download.')
        return 'ok', 200
    except Exception as e:
        logger.error(f'Webhook error: {e}')
        return 'error', 500

@app.route('/health', methods=['GET'])
def health():
    return 'AXIOM System Active', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
