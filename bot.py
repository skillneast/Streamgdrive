import logging
import re
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Apna Bot Token yahan dalein
BOT_TOKEN = "8459084440:AAEB19FqmOZz6WG3Mhg9PHoHZ0aAAAHebnQ"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# GDrive ID nikalne ka function
def extract_gdrive_id(url):
    patterns = [
        r'/file/d/([-\w]+)',
        r'id=([-\w]+)',
        r'/open\?id=([-\w]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# --- MAIN MAGIC FUNCTION (Bina API Key ke link nikalna) ---
def get_final_link(file_id):
    URL = "https://docs.google.com/uc?export=download"
    session = requests.Session()
    
    try:
        # Step 1: Request bhejo
        response = session.get(URL, params={'id': file_id}, stream=True)
        
        # Step 2: Check karo agar Google Token mang raha hai (Large files ke liye)
        token = None
        for key, value in session.cookies.items():
            if key.startswith('download_warning'):
                token = value
                break
        
        # Step 3: Agar token mila, to confirm URL banao
        if token:
            params = {'id': file_id, 'confirm': token}
            response = session.get(URL, params=params, stream=True)
        
        # Step 4: Final URL return karo (googleusercontent wala)
        return response.url
        
    except Exception as e:
        print(f"Error: {e}")
        return None

# Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔓 **No-API GDrive Bot**\n\n"
        "Link bhejo, main bina API Key ke Direct Stream Link nikal kar dunga."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    msg = await update.message.reply_text("🔄 **Processing...** (Please wait)")
    
    if "drive.google.com" in user_text:
        file_id = extract_gdrive_id(user_text)
        
        if file_id:
            # Backend process run karein
            direct_link = get_final_link(file_id)
            
            if direct_link:
                reply_text = (
                    f"✅ **Link Generated Successfully!**\n\n"
                    f"📂 **File ID:** `{file_id}`\n\n"
                    f"🔗 **Direct Stream Link:**\n`{direct_link}`\n\n"
                    f"⚠️ *Note: Ye link kuch ghanton mein expire ho sakta hai (Temporary Session Link).*\n"
                    f"▶️ *Directly VLC/MX Player mein chalega.*"
                )
                # Purana "Processing" message delete/edit karein
                await msg.edit_text(reply_text, parse_mode='Markdown')
            else:
                await msg.edit_text("❌ Link generate karne mein error aaya. Shayad file Private hai.")
        else:
            await msg.edit_text("❌ Invalid Link.")
    else:
        await msg.edit_text("Sirf Google Drive link bhejein.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot is running without API Key...")
    app.run_polling()
