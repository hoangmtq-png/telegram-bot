import os
import time
import threading
import asyncio
import requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.request import HTTPXRequest
import yt_dlp

# ---> THAY TOKEN CHUẨN ĐƯỢC CẤP BỞI @BotFather VÀO ĐÂY <---
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "🤖 Bot Telegram Download Video đang hoạt động mượt mà trên Render!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app_flask.run(host="0.0.0.0", port=port)

user_links = {}

def cleanup_downloads_folder():
    while True:
        time.sleep(1800)
        folder = "downloads"
        if os.path.exists(folder):
            now = time.time()
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path) and (now - os.path.getmtime(file_path) > 1800):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass

def get_real_tiktok_url(url):
    """Hàm giải mã link rút gọn vt.tiktok.com thành link chuẩn để tránh bị TikTok chặn"""
    if "tiktok.com" in url:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            # Gửi yêu cầu lấy lịch sử chuyển hướng (redirect) của link rút gọn
            response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            real_url = response.url.split("?")[0] # Cắt bỏ các tham số thừa phía sau
            return real_url
        except Exception:
            pass
    return url.split("?")[0]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 **TRỢ LÝ TẢI VIDEO & ÂM THANH ĐA NĂNG** 🚀\n\n"
        "✨ *Các tính năng hỗ trợ:*\n"
        "• Tải video **Facebook / Reels** chất lượng cao.\n"
        "• Tải video **TikTok không logo (No Watermark)**.\n"
        "• Tách file âm thanh **(.mp3)** từ video cực nhanh.\n\n"
        "📥 **Hãy gửi ngay link video Facebook hoặc TikTok cho tôi nhé!**"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_message = update.message
     
    is_fb = "facebook.com" in url or "fb.watch" in url or "fb.gg" in url
    is_tt = "tiktok.com" in url or "vt.tiktok.com" in url
     
    if not (is_fb or is_tt):
        await update.message.reply_text("⚠️ **Lưu ý:** Vui lòng gửi đường dẫn (link) video **Facebook** hoặc **TikTok** hợp lệ!")
        return

    async def delete_user_link():
        await asyncio.sleep(30)
        try:
            await user_message.delete()
        except Exception:
            pass
    asyncio.create_task(delete_user_link())

    user_id = update.effective_user.id
    user_links[user_id] = url
     
    checking_msg = await update.message.reply_text("⏳ **Đang kết nối tới máy chủ để lấy thông tin video...**")
     
    def check_info():
        nonlocal url
        if is_tt:
            url = get_real_tiktok_url(url)
            
        ydl_opts = {
            'quiet': True,
            'extractor_args': {
                'tiktok': {
                    'webpage_client': ['android', 'web']
                }
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', 'Video không tên')

    try:
        loop = asyncio.get_running_loop()
        video_title = await loop.run_in_executor(None, check_info)
         
        platform_name = "TikTok Không Logo" if is_tt else "Facebook"
         
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Tải Video (Chất lượng cao)", callback_data="dl_video_best")],
            [InlineKeyboardButton("🎵 Tách lấy File Nhạc (.mp3)", callback_data="dl_audio_mp3")],
            [InlineKeyboardButton("❌ Hủy thao tác", callback_data="dl_cancel")]
        ])
         
        menu_text = (
            f"🎯 **ĐÃ PHÁT HIỆN LINK {platform_name.upper()}!**\n\n"
            f"📌 **Tiêu đề:** `{video_title}`\n\n"
            "👇 **Bạn muốn xử lý video này như thế nào?**"
        )
         
        await checking_msg.edit_text(menu_text, reply_markup=keyboard, parse_mode="Markdown")
         
    except Exception as e:
        await checking_msg.edit_text(f"❌ **Không thể đọc thông tin video:**\n`{str(e)}`", parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
     
    user_id = query.from_user.id
    choice = query.data
     
    if choice == "dl_cancel":
        await query.edit_message_text("❌ **Đã hủy thao tác.** Gửi link mới bất cứ lúc nào bạn muốn nhé!", parse_mode="Markdown")
        return

    if user_id not in user_links:
        await query.message.reply_text("⚠️ **Phiên làm việc đã hết hạn. Vui lòng gửi lại link mới!**")
        return
         
    url = user_links[user_id]
    is_tt = "tiktok.com" in url or "vt.tiktok.com" in url
     
    if choice == "dl_video_best":
        status_text = "⚙️ **Đang tải video về máy chủ (Hỗ trợ file tối đa 300MB)...**"
        ydl_opts = {
            'format': 'best[filesize<300M]/best',
            'socket_timeout': 120,
            'outtmpl': f"downloads/{user_id}_%(id)s.%(ext)s",
            'extractor_args': {
                'tiktok': {
                    'webpage_client': ['android', 'web']
                }
            }
        }
        is_audio = False
    else: 
        status_text = "🎵 **Đang trích xuất và chuyển đổi file âm thanh (.mp3)...**"
        ydl_opts = {
            'format': 'bestaudio/best',
            'socket_timeout': 120,
            'outtmpl': f"downloads/{user_id}_%(id)s.%(ext)s",
            'extractor_args': {
                'tiktok': {
                    'webpage_client': ['android', 'web']
                }
            },
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        is_audio = True

    status_msg = await query.edit_message_text(status_text, parse_mode="Markdown")
    os.makedirs("downloads", exist_ok=True)

    try:
        def process_media():
            nonlocal url
            if is_tt:
                url = get_real_tiktok_url(url)
                
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if is_audio:
                    base, _ = os.path.splitext(filename)
                    filename = base + ".mp3"
                return filename, info.get('title', 'Media File')

        loop = asyncio.get_running_loop()
        file_path, title = await loop.run_in_executor(None, process_media)

        await status_msg.edit_text("📤 **Đang gửi file lên Telegram, vui lòng đợi trong giây lát...**", parse_mode="Markdown")

        with open(file_path, 'rb') as media_file:
            if is_audio:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=media_file,
                    caption=f"🎵 **Tách nhạc thành công!**\n📌 `{title}`",
                    parse_mode="Markdown"
                )
            else:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=media_file,
                    caption=f"✅ **Tải video thành công!**\n📌 `{title}`",
                    supports_streaming=True,
                    parse_mode="Markdown"
                )

        await status_msg.delete()

        reset_menu_text = (
            "✨ **Hoàn tất quá trình xử lý!**\n\n"
            "📥 **Hãy gửi tiếp link video Facebook hoặc TikTok khác nếu bạn muốn tải tiếp nhé!**"
        )
        await context.bot.send_message(chat_id=query.message.chat_id, text=reset_menu_text, parse_mode="Markdown")

        if os.path.exists(file_path):
            os.remove(file_path)
             
    except Exception as e:
        await status_msg.edit_text(f"❌ **Lỗi xử lý file:**\n`{str(e)}`", parse_mode="Markdown")

def main():
    cleanup_thread = threading.Thread(target=cleanup_downloads_folder, daemon=True)
    cleanup_thread.start()

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    custom_request = HTTPXRequest(connect_timeout=120.0, read_timeout=300.0)
     
    application = ApplicationBuilder().token(BOT_TOKEN).request(custom_request).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Bot quản lý đa năng với cơ chế chống chặn TikTok đang chạy...")
    application.run_polling()

if __name__ == '__main__':
    main()
