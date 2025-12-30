import os
import logging
from flask import Flask, request, Response
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
PORT = int(os.environ.get('PORT', 8000))

app = Flask(__name__)

async def start(update: Update, context):
    message = 'Hello! AXIOM is online!

Send me any message.'
    await update.message.reply_text(message)

async def echo(update: Update, context):
    response = f'AXIOM received: {update.message.text}'
    await update.message.reply_text(response)

application = Application.builder().token(TOKEN).updater(None).build()
application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

@app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.update_queue.put(update)
        return Response(status=200)
    except Exception as e:
        logger.error(f'Error: {e}')
        return Response(status=500)

@app.route('/health', methods=['GET'])
def health():
    return 'AXIOM System: Active', 200

async def setup():
    await application.initialize()
    await application.start()

if __name__ == '__main__':
    import asyncio
    asyncio.run(setup())
    app.run(host='0.0.0.0', port=PORT)
