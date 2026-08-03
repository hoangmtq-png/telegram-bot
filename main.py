import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
import google.generativeai as genai

from config import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY
from keep_alive import keep_alive

# Cấu hình logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

# Cấu hình AI Gemini/Grok
genai.configure(api_key=GEMINI_API_KEY)
grok_model = genai.GenerativeModel('gemini-1.5-flash')

async def start(update: Update, context):
    await update.message.reply_text("⚡ **Grok AI Pro OS** đã sẵn sàng hoạt động trên Render!", parse_mode="Markdown")

async def handle_message(update: Update, context):
    text = update.message.text
    try:
        response = grok_model.generate_content(text)
        await update.message.reply_text(f"⚡ **Grok:**\n\n{response.text}", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Lỗi AI: {e}")
        await update.message.reply_text("⚠️ Hệ thống đang bận, vui lòng thử lại sau!")

def main():
    # Khởi chạy server giữ kết nối 24/7 cho Render
    keep_alive()
    
    # Khởi chạy Telegram Bot
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logging.info("Bot đang khởi chạy polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
