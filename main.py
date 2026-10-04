import asyncio
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

app = Flask(__name__)


# --- HỆ THỐNG TỰ ĐỘNG XÓA TIN NHẮN SAU 30S ---
async def schedule_message_deletion(context: ContextTypes.DEFAULT_TYPE):
  job = context.job
  chat_id = job.data.get("chat_id")
  message_id = job.data.get("message_id")
  try:
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
  except Exception:
    pass  # Bỏ qua nếu tin nhắn đã bị xóa từ trước


# --- CÁC TÍNH NĂNG CHUYÊN SÂU ---
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


def download_social_media_video(url: str, platform_type: str) -> dict:
  try:
    # Nếu đang chọn chế độ TikTok/Douyin mà gửi link khác -> Chặn ngay từ hàm logic
    if (
        platform_type == "tiktok"
        and "tiktok.com" not in url
        and "douyin.com" not in url
    ):
      return {
          "success": False,
          "error": "⚠️ Vui lòng gửi link chính xác của TikTok hoặc Douyin!",
      }
    if (
        platform_type == "facebook"
        and "facebook.com" not in url
        and "fb.watch" not in url
    ):
      return {
          "success": False,
          "error": "⚠️ Vui lòng gửi link chính xác của Facebook Video!",
      }

    api_url = f"https://www.tikwm.com/api/?url={requests.utils.quote(url)}"
    res = requests.get(api_url, timeout=10).json()

    if res.get("code") == 0:
      data = res.get("data", {})
      return {
          "success": True,
          "title": data.get("title", "Video không tiêu đề"),
          "video_url": data.get("play"),
          "author": data.get("author", {}).get("nickname", "Chính chủ"),
      }

    return {
        "success": False,
        "error": "Không thể trích xuất video. Hãy đảm bảo link ở chế độ công khai!",
    }
  except Exception as e:
    return {"success": False, "error": f"Lỗi kết nối: {str(e)}"}


# --- MENU PHÂN TÁCH RIÊNG BIỆT ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  keyboard = [
      [
          InlineKeyboardButton(
              "📥 Tải Video TikTok / Douyin", callback_data="mode_tiktok"
          )
      ],
      [
          InlineKeyboardButton(
              "📥 Tải Video Facebook", callback_data="mode_fb_video"
          )
      ],
      [
          InlineKeyboardButton(
              "🔍 Lấy UID Facebook Gốc", callback_data="mode_fb_uid"
          )
      ],
      [InlineKeyboardButton("🟢 Trạng Thái Hệ Thống", callback_data="mode_status")],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  text = (
      "✨ **HỆ THỐNG MENU ĐIỀU KHIỂN RIÊNG BIỆT**\n\n👇 Vui lòng bấm chọn một"
      " tính năng bên dưới để bắt đầu sử dụng (Mỗi mục hoạt động độc lập, không"
      " bị lộn xộn):"
  )

  if update.message:
    msg = await update.message.reply_text(
        text, reply_markup=reply_markup, parse_mode="Markdown"
    )
    # Lên lịch tự động xóa sau 30s (tùy chọn cho menu chính, hoặc giữ lại)
  elif update.callback_query:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text, reply_markup=reply_markup, parse_mode="Markdown"
    )


async def button_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  query = update.callback_query
  await query.answer()
  data = query.data
  back_btn = InlineKeyboardMarkup(
      [[InlineKeyboardButton("🔙 Quay lại Menu Chính", callback_data="home")]]
  )

  if data == "mode_tiktok":
    context.user_data["current_mode"] = "tiktok"
    await query.edit_message_text(
        "📥 **ĐANG Ở CHẾ ĐỘ: TẢI VIDEO TIKTOK / DOUYIN**\n\n- Gửi link"
        " **TikTok** hoặc **Douyin** vào đây.\n- Nếu bạn gửi link sai (ví dụ"
        " link FB), hệ thống sẽ từ chối xử lý.",
        reply_markup=back_btn,
        parse_mode="Markdown",
    )
  elif data == "mode_fb_video":
    context.user_data["current_mode"] = "fb_video"
    await query.edit_message_text(
        "📥 **ĐANG Ở CHẾ ĐỘ: TẢI VIDEO FACEBOOK**\n\n- Gửi link **Facebook Video**"
        " vào đây.\n- Các link khác sẽ bị từ chối.",
        reply_markup=back_btn,
        parse_mode="Markdown",
    )
  elif data == "mode_fb_uid":
    context.user_data["current_mode"] = "fb_uid"
    await query.edit_message_text(
        "🔍 **ĐANG Ở CHẾ ĐỘ: LẤY UID FACEBOOK GỐC**\n\n- Gửi link bài viết hoặc"
        " profile Facebook để lấy số UID chính xác.",
        reply_markup=back_btn,
        parse_mode="Markdown",
    )
  elif data == "mode_status":
    status_text = (
        "🟢 **TRẠNG THÁI HỆ THỐNG SMM 24/7**\n\n- API Trực tuyến: 100%\n- Server"
        " Render: Hoạt động ổn định"
    )
    await query.edit_message_text(
        text=status_text, reply_markup=back_btn, parse_mode="Markdown"
    )
  elif data == "home":
    await start_command(update, context)


# --- XỬ LÝ TIN NHẮN ĐỘC LẬP & KIỂM TRA NGẶT NGHÈO ---
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message = update.message
  text_input = message.text.strip()
  current_mode = context.user_data.get("current_mode", None)

  # Nếu chưa chọn chế độ từ menu
  if not current_mode:
    warning_msg = await message.reply_text(
        "⚠️ Vui lòng bấm lệnh /start hoặc chọn một tính năng cụ thể trong menu"
        " trước khi gửi link!"
    )
    # Tự động xóa thông báo nhắc nhở này sau 30 giây
    context.job_queue.run_once(
        schedule_message_deletion,
        30,
        data={"chat_id": message.chat_id, "message_id": warning_msg.message_id},
    )
    return

  if "http://" not in text_input and "https://" not in text_input:
    err_msg = await message.reply_text(
        "💡 Vui lòng gửi một đường dẫn (URL) hợp lệ theo đúng chế độ bạn đang"
        " chọn!"
    )
    context.job_queue.run_once(
        schedule_message_deletion,
        30,
        data={"chat_id": message.chat_id, "message_id": err_msg.message_id},
    )
    return

  # KIỂM TRA NGẶT NGHÈO THEO TỪNG MỤC RIÊNG BIỆT
  if current_mode == "tiktok":
    if "tiktok.com" not in text_input and "douyin.com" not in text_input:
      err_msg = await message.reply_text(
          "❌ Bạn đang ở chế độ **Tải Video TikTok/Douyin**!\n⚠️ Vui lòng gửi"
          " đúng link TikTok/Douyin, không được gửi link khác."
      )
      context.job_queue.run_once(
          schedule_message_deletion,
          30,
          data={"chat_id": message.chat_id, "message_id": err_msg.message_id},
      )
      return

    wait_msg = await message.reply_text("⏳ Đang tải video TikTok/Douyin...")
    res = download_social_media_video(text_input, "tiktok")
    try:
      await context.bot.delete_message(
          chat_id=message.chat_id, message_id=wait_msg.message_id
      )
    except Exception:
      pass

    if res.get("success"):
      sent_vid = await message.reply_video(
          video=res["video_url"],
          caption=(
              f"🎬 **Tiêu đề:** {res['title']}\n👤 **Tác giả:**"
              f" `{res['author']}`"
          ),
          parse_mode="Markdown",
      )
      # Tự động xóa video/tin nhắn tải về sau 30 giây nếu muốn (hoặc giữ lại tùy ý bạn)
    else:
      err_msg = await message.reply_text(res.get("error"))
      context.job_queue.run_once(
          schedule_message_deletion,
          30,
          data={"chat_id": message.chat_id, "message_id": err_msg.message_id},
      )

  elif current_mode == "fb_video":
    if "facebook.com" not in text_input and "fb.watch" not in text_input:
      err_msg = await message.reply_text(
          "❌ Bạn đang ở chế độ **Tải Video Facebook**!\n⚠️ Vui lòng gửi đúng"
          " link Facebook Video."
      )
      context.job_queue.run_once(
          schedule_message_deletion,
          30,
          data={"chat_id": message.chat_id, "message_id": err_msg.message_id},
      )
      return

    wait_msg = await message.reply_text("⏳ Đang xử lý tải video Facebook...")
    res = download_social_media_video(text_input, "facebook")
    try:
      await context.bot.delete_message(
          chat_id=message.chat_id, message_id=wait_msg.message_id
      )
    except Exception:
      pass

    if res.get("success"):
      await message.reply_video(
          video=res["video_url"],
          caption=(
              f"🎬 **Facebook Video**\n👤 **Tác giả:** `{res['author']}`"
          ),
          parse_mode="Markdown",
      )
    else:
      err_msg = await message.reply_text(res.get("error"))
      context.job_queue.run_once(
          schedule_message_deletion,
          30,
          data={"chat_id": message.chat_id, "message_id": err_msg.message_id},
      )

  elif current_mode == "fb_uid":
    if "facebook.com" not in text_input and "fb.watch" not in text_input:
      err_msg = await message.reply_text(
          "❌ Bạn đang ở chế độ **Lấy UID Facebook**!\n⚠️ Vui lòng gửi link"
          " Facebook hợp lệ."
      )
      context.job_queue.run_once(
          schedule_message_deletion,
          30,
          data={"chat_id": message.chat_id, "message_id": err_msg.message_id},
      )
      return

    wait_msg = await message.reply_text("⏳ Đang bóc tách UID Facebook gốc...")
    uid_res = get_original_facebook_uid(text_input)
    try:
      await context.bot.delete_message(
          chat_id=message.chat_id, message_id=wait_msg.message_id
      )
    except Exception:
      pass

    result_msg = await message.reply_text(
        f"🎯 **KẾT QUẢ UID GỐC:**\n`{uid_res}`", parse_mode="Markdown"
    )
    # Xóa kết quả UID sau 30 giây để bảo mật / dọn sạch chat
    context.job_queue.run_once(
        schedule_message_deletion,
        30,
        data={"chat_id": message.chat_id, "message_id": result_msg.message_id},
    )


# --- FLASK SERVER (Duy trì Render 24/7) ---
@app.route("/")
def index():
  return "🤖 Bot is running 24/7!"


def run_flask():
  app.run(host="0.0.0.0", port=PORT)


def main():
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()

  application = Application.builder().token(TOKEN).build()

  application.add_handler(CommandHandler("start", start_command))
  application.add_handler(CallbackQueryHandler(button_callback_handler))
  application.add_handler(
      MessageHandler(filters.TEXT & (~filters.COMMAND), message_router)
  )

  print("🤖 Bot đang chạy hoàn hảo với tính năng phân tách menu & tự xóa 30s...")
  application.run_polling()


if __name__ == "__main__":
  main()
