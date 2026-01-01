import os

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
COOKIE_BASE64 = os.environ.get('COOKIE_BASE64', '')
TELEGRAM_API = f'https://api.telegram.org/bot{TOKEN}'
TEMP_DIR = '/tmp'
MAX_FILE_SIZE_MB = 48
MAX_VIDEO_DURATION = 300
