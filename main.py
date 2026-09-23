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
    return "🤖 Bot Telegram Download Video đang hoạt động!"

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

def get_tiktok_direct_download_url(url):
    """Sử dụng API trung gian công khai để lấy link trực tiếp và tiêu đề TikTok, né tuyệt đối lỗi chặn IP Cloud của yt-dlp"""
    try:
        # Giải mã link rút gọn trước
        headers_init = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15"}
        if "vt.tiktok.com" in url or "vm.tiktok.com" in url:
            res = requests.head(url, headers=headers_init, allow_redirects=True, timeout=10)
            url = res.url.split("?")[0]
        else:
            url = url.split("?")[0]

        # Gọi Cobalt API công khai để trích xuất link video không logo
        api_url = "https://co.wuk.sh/api/json"
        payload = {
            "url": url,
            "vQuality": "max"
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        data = response.json()
        
        if data.get("status") == "stream" or data.get("status") == "redirect":
            direct_url = data.get("url")
            # Trả về link trực tiếp và tiêu đề giả lập an toàn
            return direct_url, "TikTok Video (No Watermark)"
        elif data.get("status") == "picker":
            # Trường hợp video dạng slide ảnh, lấy ảnh đầu tiên hoặc link stream
            direct_url = data["picker"][0]["url"]
            return direct_url, "TikTok Slide/Video"
            
    except Exception as e:
        print(f"Lỗi API trích xuất TikTok: {e}")
    
    return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 **TRỢ LÝ TẢI VIDEO & ÂM THANH ĐA NĂNG** 🚀\n\n"
        "• Tải video **Facebook / Reels** chất lượng cao.\n"
        "• Tải video **TikTok không logo**.\n"
        "• Tách file âm thanh **(.mp3)** từ video cực nhanh.\n\n"
        "📥 **Hãy gửi ngay link video cho tôi nhé!**"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_message = update.message
     
    is_fb = "facebook.com" in url or "fb.watch" in url or "fb.gg" in url
    is_tt = "tiktok.com" in url or "vt.tiktok.com" in url or "vm.tiktok.com" in url
     
    if not (is_fb or is_tt):
        await update.message.reply_text("⚠️ Vui lòng gửi link video **Facebook** hoặc **TikTok** hợp lệ!")
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
     
    checking_msg = await update.message.reply_text("⏳ **Đang kết nối tới máy chủ lấy thông tin video...**", parse_mode="Markdown")
     
    def check_info_sync():
        if is_tt:
            _, title = get_tiktok_direct_download_url(url)
            return title if title else "Video TikTok"
        else:
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('title', 'Video Facebook')

    try:
        loop = asyncio.get_running_loop()
        video_title = await loop.run_in_executor(None, check_info_sync)
         
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
        await query.edit_message_text("❌ Đã hủy thao tác.", parse_mode="Markdown")
        return

    if user_id not in user_links:
        await query.message.reply_text("⚠️ Phiên làm việc đã hết hạn. Vui lòng gửi lại link mới!")
        return
         
    url = user_links[user_id]
    is_tt = "tiktok.com" in url or "vt.tiktok.com" in url or "vm.tiktok.com" in url
     
    status_msg = await query.edit_message_text("⚙️ **Đang tải file về máy chủ...**", parse_mode="Markdown")
    os.makedirs("downloads", exist_ok=True)

    try:
        def process_download_sync():
            file_path = ""
            title = "Media File"
            
            if is_tt:
                direct_url, title = get_tiktok_direct_download_url(url)
                if not direct_url:
                    raise Exception("Không thể lấy link trực tiếp từ TikTok API.")
                
                # Tải file trực tiếp qua requests từ link direct cực kỳ mượt mà
                res = requests.get(direct_url, stream=True, timeout=60)
                file_path = os.path.join("downloads", f"{user_id}_tiktok.mp4")
                with open(file_path, 'wb') as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                if choice == "dl_audio_mp3":
                    # Nếu người dùng chọn lấy mp3, dùng yt-dlp hoặc chuyển đổi ffmpeg đơn giản ở đây nếu cần
                    # Tạm thời trả về file mp4 hoặc trích xuất audio bằng yt-dlp từ direct_url
                    pass
            else:
                # Xử lý cho Facebook bằng yt-dlp bình thường (Facebook không chặn IP datacenter gắt như TikTok)
                if choice == "dl_video_best":
                    ydl_opts = {
                        'format': 'best[filesize<300M]/best',
                        'socket_timeout': 120,
                        'outtmpl': f"downloads/{user_id}_%(id)s.%(ext)s",
                    }
                else:
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'socket_timeout': 120,
                        'outtmpl': f"downloads/{user_id}_%(id)s.%(ext)s",
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                    }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    file_path = ydl.prepare_filename(info)
                    if choice == "dl_audio_mp3":
                        base, _ = os.path.splitext(file_path)
                        file_path = base + ".mp3"
                    title = info.get('title', 'Facebook Video')

            return file_path, title

        loop = asyncio.get_running_loop()
        file_path, title = await loop.run_in_executor(None, process_download_sync)

        await status_msg.edit_text("📤 **Đang gửi file lên Telegram...**", parse_mode="Markdown")

        with open(file_path, 'rb') as media_file:
            if choice == "dl_audio_mp3" and not is_tt:
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=media_file, caption=f"🎵 {title}", parse_mode="Markdown")
            else:
                await context.bot.send_video(chat_id=query.message.chat_id, video=media_file, caption=f"✅ {title}", supports_streaming=True, parse_mode="Markdown")

        await status_msg.delete()
        await context.bot.send_message(chat_id=query.message.chat_id, text="✨ Hoàn tất! Hãy gửi link tiếp theo nếu bạn muốn.", parse_mode="Markdown")

        if os.path.exists(file_path):
            os.remove(file_path)
             
    except Exception as e:
        await status_msg.edit_text(f"❌ **Lỗi xử lý file:**\n`{str(e)}`", parse_mode="Markdown")

def main():
    threading.Thread(target=cleanup_downloads_folder, daemon=True).start()
    threading.Thread(target=run_flask, daemon=True).start()

    custom_request = HTTPXRequest(connect_timeout=120.0, read_timeout=300.0)
    application = ApplicationBuilder().token(BOT_TOKEN).request(custom_request).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Bot đã sẵn sàng với cơ chế API chuyển hướng chống chặn TikTok...")
    application.run_polling()

if __name__ == '__main__':
    main()
