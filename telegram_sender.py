import requests
import logging
from config import TELEGRAM_API

logger = logging.getLogger(__name__)

def send_message(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        response = requests.post(f'{TELEGRAM_API}/sendMessage', json=payload)
        return response.json()
    except Exception as e:
        logger.error(f'Send message error: {e}')
        return None

def send_video(chat_id, video_path, caption=None, has_spoiler=False):
    try:
        with open(video_path, 'rb') as video:
            files = {'video': video}
            data = {'chat_id': chat_id, 'supports_streaming': True}
            if caption:
                data['caption'] = caption
            if has_spoiler:
                data['has_spoiler'] = has_spoiler
            response = requests.post(f'{TELEGRAM_API}/sendVideo', data=data, files=files, timeout=300)
        return response.json()
    except Exception as e:
        logger.error(f'Send video error: {e}')
        return None

def send_photo(chat_id, photo_path, caption=None):
    try:
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
            response = requests.post(f'{TELEGRAM_API}/sendPhoto', data=data, files=files, timeout=120)
        return response.json()
    except Exception as e:
        logger.error(f'Send photo error: {e}')
        return None

def send_audio(chat_id, audio_path, title=None):
    try:
        with open(audio_path, 'rb') as audio:
            files = {'audio': audio}
            data = {'chat_id': chat_id}
            if title:
                data['title'] = title
            response = requests.post(f'{TELEGRAM_API}/sendAudio', data=data, files=files, timeout=180)
        return response.json()
    except Exception as e:
        logger.error(f'Send audio error: {e}')
        return None

def create_inline_keyboard(buttons):
    return {'inline_keyboard': buttons}
