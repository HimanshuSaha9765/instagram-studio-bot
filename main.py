import os
import logging
import requests
from flask import Flask, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_API = f'https://api.telegram.org/bot{TOKEN}/sendMessage'

app = Flask(__name__)

def send_telegram_message(chat_id, text):
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    try:
        response = requests.post(TELEGRAM_API, json=payload)
        return response.json()
    except Exception as e:
        logger.error(f'Send message error: {e}')
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
                    send_telegram_message(chat_id, 'Hello! AXIOM is online! Send me any message.')
                else:
                    send_telegram_message(chat_id, f'AXIOM received: {text}')
        
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
