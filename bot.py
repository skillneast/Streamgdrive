import os
import re
import requests
import asyncio
from flask import Flask, request, redirect, Response
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
# Naya Revoked Token Yahan Dalein
BOT_TOKEN = "8459084440:AAHFpH9Q10yJAOXwNq8-UFqbYpQMALtct2Q" 

# Render automatically ye URL set karta hai
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")

app = Flask(__name__)

# --- GDRIVE LINK GENERATOR (Improved) ---
def get_gdrive_direct_link(file_id):
    """
    Advanced logic to get confirm token via Cookies or Page Content
    """
    url = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    
    try:
        response = session.get(url, params={'id': file_id}, stream=True)
        
        token = None
        
        # Method 1: Check Cookies
        for key, value in session.cookies.items():
            if key.startswith('download_warning'):
                token = value
                break
        
        # Method 2: Check Page Content (Agar cookie fail ho jaye)
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
        print(f"Error generating link: {e}")
        return None

# --- FLASK ROUTES ---

@app.route('/')
def home():
    return "Bot is Alive & Running!"

# Ye route video stream karega
@app.route('/stream/<file_id>')
def stream_video(file_id):
    direct_link = get_gdrive_direct_link(file_id)
    
    if direct_link:
        # Redirect user to the fresh Google Link
        return redirect(direct_link, code=302)
    else:
        return "<h3>Error: Cannot generate link. File might be Private or Deleted.</h3>", 404

# Telegram Updates Webhook ke through aayenge (No Polling)
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
async def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
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
    await update.message.reply_text(
        "✅ **Bot Fixed & Ready!**\n\nLink bhejo, main Stream Link dunga."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    if "drive.google.com" in user_text:
        file_id = extract_gdrive_id(user_text)
        if file_id:
            # Render URL + Stream Route
            # Slash (/) ka dhyan rakhein
            base = RENDER_EXTERNAL_URL.rstrip('/')
            stream_link = f"{base}/stream/{file_id}"
            
            await update.message.reply_text(
                f"🎬 **Stream Link Generated**\n\n"
                f"🔗 **Link:**\n`{stream_link}`\n\n"
                f"▶️ **Note:** Is link ko VLC me daalo. Jab bhi play karoge, ye naya fresh link layega.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Invalid Google Drive Link")

# --- APP SETUP ---
# Global Bot Application
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# Webhook Setup Function
def set_webhook():
    webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
    print(f"Setting Webhook to: {webhook_url}")
    # Sync request to set webhook
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}")

if __name__ == '__main__':
    # Webhook set karein
    set_webhook()
    
    # Flask Server Run Karein
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
