import os
import logging
from flask import Flask, request
from telegram import Update, Bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
bot = Bot(token=TOKEN)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        
        if update.message and update.message.text:
            chat_id = update.message.chat_id
            text = update.message.text
            
            if text == '/start':
                bot.send_message(chat_id=chat_id, text='Hello! AXIOM is online! Send me any message.')
            else:
                bot.send_message(chat_id=chat_id, text='AXIOM received: ' + text)
        
        return 'ok', 200
    except Exception as e:
        logger.error('Error: ' + str(e))
        return 'error', 500

@app.route('/health', methods=['GET'])
def health():
    return 'AXIOM System Active', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
