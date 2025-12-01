import os
import re
import requests
import threading
from flask import Flask, redirect
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = "8459084440:AAEB19FqmOZz6WG3Mhg9PHoHZ0aAAAHebnQ"  # Apna Token Dalein
# Render automatic URL set karega, lekin agar local chala rahe ho to localhost
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")
# ---------------------

# Flask Web Server Setup
app = Flask(__name__)

def get_gdrive_direct_link(file_id):
    """
    Ye function Google Drive se fresh download link nikalta hai
    bina API Key ke, Cookies handle karke.
    """
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    
    try:
        response = session.get(URL, params={'id': file_id}, stream=True)
        
        token = None
        for key, value in session.cookies.items():
            if key.startswith('download_warning'):
                token = value
                break
        
        if token:
            params = {'id': file_id, 'confirm': token}
            response = session.get(URL, params=params, stream=True)
            
        return response.url
    except:
        return None

# --- FLASK ROUTE (Magic Hoti Hai Yahan) ---
@app.route('/stream/<file_id>')
def stream_video(file_id):
    # Jab VLC ye link open karega, hum fresh link nikal kar redirect karenge
    direct_link = get_gdrive_direct_link(file_id)
    if direct_link:
        return redirect(direct_link, code=302)
    else:
        return "Error: File not found or Private", 404

@app.route('/')
def home():
    return "Bot is Running! Telegram par jao."

# --- TELEGRAM BOT LOGIC ---
def extract_gdrive_id(url):
    patterns = [r'/file/d/([-\w]+)', r'id=([-\w]+)', r'/open\?id=([-\w]+)']
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Link bhejo, main permanent stream link dunga.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    if "drive.google.com" in user_text:
        file_id = extract_gdrive_id(user_text)
        if file_id:
            # Hum user ko Apne Server ka link denge, Google ka nahi
            # Ye link kabhi expire nahi hoga
            permanent_link = f"{BASE_URL}/stream/{file_id}"
            
            await update.message.reply_text(
                f"✅ **Permanent Stream Link**\n\n"
                f"🔗 **Link:**\n`{permanent_link}`\n\n"
                f"▶️ Isse VLC/MX Player me dalo. Ye hamesha chalega.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Invalid Link")
    else:
        await update.message.reply_text("Send GDrive Link Only")

# --- RUNNING BOTH FLASK & BOT ---
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Flask ko alag thread me chalana padega
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Telegram Bot Start
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot + Server Running...")
    bot_app.run_polling()
