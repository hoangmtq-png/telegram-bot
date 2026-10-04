import logging
import os
import re
import threading
import requests
from flask import Flask, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- CẤU HÌNH HỆ THỐNG ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

# Khởi tạo Flask App đáp ứng yêu cầu port của Render
app = Flask(__name__)


# --- CÁC TÍNH NĂNG NÂNG CAO ---
def get_original_facebook_uid(url: str) -> str:
  try:
    if "id=" in url:
      match = re.search(r"id=(\d+)", url)
      if match:
        return match.group(1)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    }
    response = requests.get(
        url, headers=headers, allow_redirects=True, timeout=10
    )
    final_url = response.url

    match_id = re.search(r"id=(\d+)", final_url)
    if match_id:
      return match_id.group(1)

    path_match = re.findall(r"facebook\.com/([^/?]+)", final_url)
    if path_match:
      username = path_match[0]
      if username in ["profile.php", "pages", "groups", "watch", "reel"]:
        return f"Link gốc: {final_url}"
      return f"Username: `{username}`\nLink: {final_url}"

    return "Không tìm thấy định dạng URL Facebook hợp lệ."
  except Exception as e:
    return f"Lỗi xử lý UID: {str(e)}"


def download_social_media_video(url: str) -> dict:
  try:
    api_url = f"https://www.tikwm.com/api/?url={requests.utils.quote(url)}"
    res = requests.get(api_url, timeout=10).json()

    if res.get("code") == 0:
      data = res.get("data", {})
      return {
          "success": True,
          "title": data.get("title", "Video không tiêu đề"),
          "video_url": data.get("play"),
          "author": data.get("author", {}).get("nickname", "Chính chủ"),
          "platform": "TikTok / Douyin / FB",
      }

    return {
        "success": False,
        "error": "Không thể trích xuất video từ liên kết này.",
    }
  except Exception as e:
    return {"success": False, "error": f"Lỗi kết nối: {str(e)}"}


# --- GIAO DIỆN MENU TELEGRAM ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  keyboard = [
      [
          InlineKeyboardButton(
              "📥 Tải Video (TikTok / Douyin / FB)", callback_data="menu_download"
          )
      ],
      [
          InlineKeyboardButton(
              "🔍 Rút Gọn & Lấy UID Facebook Gốc", callback_data="menu_uid"
          )
      ],
      [
          InlineKeyboardButton(
              "🟢 Trạng Thái Hệ Thống SMM (24/7)", callback_data="menu_status"
          )
      ],
      [
          InlineKeyboardButton(
              "⚙️ Hướng Dẫn & Hỗ Trợ", callback_data="menu_help"
          )
      ],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  welcome_text = (
      f"✨ Chào mừng **{user.first_name}** đến với hệ thống **Smart SMM & Media"
      " Bot**!\n\n👇 Chọn tính năng bên dưới hoặc gửi trực tiếp Link:"
  )

  if update.message:
    await update.message.reply_text(
        welcome_text, reply_markup=reply_markup, parse_mode="Markdown"
    )
  elif update.callback_query:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text=welcome_text, reply_markup=reply_markup, parse_mode="Markdown"
    )


async def button_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  query = update.callback_query
  await query.answer()
  data = query.data
  back_keyboard = InlineKeyboardMarkup(
      [[InlineKeyboardButton("🔙 Quay lại Menu Chính", callback_data="menu_home")]]
  )

  if data == "menu_download":
    context.user_data["active_mode"] = "download"
    await query.edit_message_text(
        "📥 **CHẾ ĐỘ TẢI VIDEO ĐANG BẬT**\n\nGửi trực tiếp link video vào đây!",
        reply_markup=back_keyboard,
        parse_mode="Markdown",
    )
  elif data == "menu_uid":
    context.user_data["active_mode"] = "uid"
    await query.edit_message_text(
        "🔍 **CHẾ ĐỘ LẤY UID FACEBOOK ĐANG BẬT**\n\nGửi link Facebook vào đây!",
        reply_markup=back_keyboard,
        parse_mode="Markdown",
    )
  elif data == "menu_status":
    status_text = (
        "🟢 **HỆ THỐNG DỊCH VỤ MẠNG XÃ HỘI (24/7)**\n\n- Trạng thái: Hoạt"
        " động ổn định 100%\n- Server: Render Cloud Online"
    )
    await query.edit_message_text(
        text=status_text, reply_markup=back_keyboard, parse_mode="Markdown"
    )
  elif data == "menu_help":
    await query.edit_message_text(
        "⚙️ **HƯỚNG DẪN:** Gửi link để bot tự động xử lý.",
        reply_markup=back_keyboard,
        parse_mode="Markdown",
    )
  elif data == "menu_home":
    await start_command(update, context)


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text_input = update.message.text.strip()
  current_mode = context.user_data.get("active_mode", "download")

  if "http://" in text_input or "https://" in text_input:
    if "facebook.com" in text_input or "fb.watch" in text_input:
      if current_mode == "uid" or "profile.php" in text_input:
        await update.message.reply_text("⏳ Đang phân tích UID gốc...")
        uid_res = get_original_facebook_uid(text_input)
        await update.message.reply_text(
            f"🎯 **KẾT QUẢ UID:**\n`{uid_res}`", parse_mode="Markdown"
        )
        return

    if any(
        d in text_input
        for d in ["tiktok.com", "douyin.com", "facebook.com", "fb.watch"]
    ):
      await update.message.reply_text("⏳ Đang xử lý tải video...")
      res = download_social_media_video(text_input)
      if res.get("success") and res.get("video_url"):
        try:
          await update.message.reply_video(
              video=res["video_url"],
              caption=(
                  f"🎬 **Tiêu đề:** {res['title']}\n👤 **Tác giả:**"
                  f" `{res['author']}`"
              ),
              parse_mode="Markdown",
          )
        except Exception:
          await update.message.reply_text(
              f"✅ Link tải trực tiếp:\n{res['video_url']}"
          )
      else:
        await update.message.reply_text("⚠️ Không thể tải video từ link này.")
    else:
      await update.message.reply_text("⚠️ Đường dẫn không được hỗ trợ!")
  else:
    await update.message.reply_text("💡 Vui lòng gửi một đường dẫn (URL) hợp lệ!")


# --- FLASK SERVER ROUTES (Giữ port render mở 24/7) ---
@app.route("/")
def index():
  return "🤖 Telegram Bot is running smoothly on Render 24/7!"


def run_flask():
  app.run(host="0.0.0.0", port=PORT)


def main():
  # Khởi chạy Flask ở một Thread riêng biệt để mở Port HTTP cho Render
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()
  logger.info(
      f"🚀 Flask Web Server đã mở tại cổng {PORT} để đáp ứng yêu cầu của"
      " Render."
  )

  # Khởi tạo Telegram Bot chạy Polling trực tiếp ở luồng chính (Ổn định tuyệt đối)
  application = Application.builder().token(TOKEN).build()

  application.add_handler(CommandHandler("start", start_command))
  application.add_handler(CallbackQueryHandler(button_callback_handler))
  application.add_handler(
      MessageHandler(filters.TEXT & (~filters.COMMAND), message_router)
  )

  print("🤖 Telegram Bot đang chạy chế độ Polling mượt mà...")
  application.run_polling()


if __name__ == "__main__":
  main()
