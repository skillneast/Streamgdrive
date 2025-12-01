import os
import re
import requests
import asyncio
from flask import Flask, request, redirect
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = "8459084440:AAHFpH9Q10yJAOXwNq8-UFqbYpQMALtct2Q"  # Apna Token Dalein
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")

app = Flask(__name__)

# Global Bot Application
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
# Flag to check if bot is initialized
bot_initialized = False

# --- GDRIVE LINK GENERATOR ---
def get_gdrive_direct_link(file_id):
    url = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    try:
        response = session.get(url, params={'id': file_id}, stream=True)
        token = None
        for key, value in session.cookies.items():
            if key.startswith('download_warning'):
                token = value
                break
        if not token:
            content = response.text
            match = re.search(r'confirm=([a-zA-Z0-9_]+)', content)
            if match:
                token = match.group(1)
        if token:
            params = {'id': file_id, 'confirm': token}
            response = session.get(url, params=params, stream=True)
        return response.url
    except Exception as e:
        print(f"Error: {e}")
        return None

# --- FLASK ROUTES ---
@app.route('/')
def home():
    return "Bot is Alive. Go to Telegram."

@app.route('/stream/<file_id>')
def stream_video(file_id):
    direct_link = get_gdrive_direct_link(file_id)
    if direct_link:
        return redirect(direct_link, code=302)
    else:
        return "Error: File Private or Deleted", 404

# --- WEBHOOK ROUTE (ASYNC FIX) ---
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
async def telegram_webhook():
    global bot_initialized
    
    # Bot ko pehli baar request aane par initialize karein
    if not bot_initialized:
        await bot_app.initialize()
        await bot_app.start()
        bot_initialized = True

    # Update process karein
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, bot_app.bot)
    await bot_app.process_update(update)
    
    return 'OK', 200

# --- BOT LOGIC ---
def extract_gdrive_id(url):
    patterns = [r'/file/d/([-\w]+)', r'id=([-\w]+)', r'/open\?id=([-\w]+)']
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot Ready! Link bhejo.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if "drive.google.com" in user_text:
        file_id = extract_gdrive_id(user_text)
        if file_id:
            base = RENDER_EXTERNAL_URL.rstrip('/')
            stream_link = f"{base}/stream/{file_id}"
            await update.message.reply_text(
                f"✅ **Stream Link:**\n`{stream_link}`\n\nVLC me paste karo.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Invalid Link")
    else:
        await update.message.reply_text("Send GDrive Link Only")

# --- HANDLERS ADDING ---
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# --- WEBHOOK SETTER ---
def set_webhook():
    webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
    print(f"Setting Webhook: {webhook_url}")
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}")
    except Exception as e:
        print(f"Webhook Set Error: {e}")

if __name__ == '__main__':
    # Pehle webhook set karein
    set_webhook()
    
    # Phir Flask Server chalayein
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
