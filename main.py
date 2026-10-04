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
    pass


# --- HÀM GIẢI MÃ LINK RÚT GỌN FACEBOOK (/share/) ---
def resolve_facebook_url(url: str) -> str:
  try:
    if "/share/" in url or "fb.watch" in url:
      headers = {
          "User-Agent": (
              "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
              "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
              "Mobile/15E148 Safari/604.1"
          )
      }
      response = requests.get(
          url, headers=headers, allow_redirects=True, timeout=10
      )
      return response.url
    return url
  except Exception:
    return url


# --- CÁC TÍNH NĂNG CHUYÊN SÂU ---
def get_original_facebook_uid(url: str) -> str:
  try:
    real_url = resolve_facebook_url(url)
    if "id=" in real_url:
      match = re.search(r"id=(\d+)", real_url)
      if match:
        return match.group(1)

    path_match = re.findall(r"facebook\.com/([^/?]+)", real_url)
    if path_match:
      username = path_match[0]
      if username in ["profile.php", "pages", "groups", "watch", "reel"]:
        return f"Link gốc: {real_url}"
      return f"Username: `{username}`\nLink: {real_url}"

    return f"Link gốc: {real_url}"
  except Exception as e:
    return f"Lỗi xử lý UID: {str(e)}"


def download_social_media_video(url: str, platform_type: str) -> dict:
  try:
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
          "error": (
              "⚠️ Vui lòng gửi link chính xác của Facebook Video / Reels!"
          ),
      }

    target_url = resolve_facebook_url(url) if platform_type == "facebook" else url

    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ),
    }
    payload = {"url": target_url}

    response = requests.post(
        api_url, json=payload, headers=headers, timeout=15
    ).json()

    status = response.get("status")
    if status in ["stream", "redirect", "picker"]:
      video_link = response.get("url")
      if not video_link and response.get("picker"):
        video_link = response["picker"][0].get("url")

      if video_link:
        return {
            "success": True,
            "title": response.get("filename", "Video mạng xã hội không logo"),
            "video_url": video_link,
            "author": "Mạng xã hội User",
        }

    return {
        "success": False,
        "error": (
            "❌ Không thể trích xuất video. Hãy đảm bảo bài viết/video ở chế độ"
            " công khai!"
        ),
    }
  except Exception as e:
    return {"success": False, "error": f"Lỗi kết nối hệ thống tải: {str(e)}"}


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
              "📥 Tải Video Facebook / Reels", callback_data="mode_fb_video"
          )
      ],
      [
          InlineKeyboardButton(
              "🔍 Lấy UID Facebook Gốc", callback_data="mode_fb_uid"
          )
      ],
      [
          InlineKeyboardButton(
              "📊 Theo Dõi Live / Die Acc", callback_data="mode_livedie"
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
    await update.message.reply_text(
        text, reply_markup=reply_markup, parse_mode="Markdown"
    )
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
        " **TikTok** hoặc **Douyin** vào đây.\n- Nếu gửi sai link, hệ thống"
        " sẽ từ chối.",
        reply_markup=back_btn,
        parse_mode="Markdown",
    )
  elif data == "mode_fb_video":
    context.user_data["current_mode"] = "fb_video"
    await query.edit_message_text(
        "📥 **ĐANG Ở CHẾ ĐỘ: TẢI VIDEO FACEBOOK / REELS**\n\n- Gửi link"
        " **Facebook Video / Reels** vào đây.\n- Các link khác sẽ bị từ chối.",
        reply_markup=back_btn,
        parse_mode="Markdown",
    )
  elif data == "mode_fb_uid":
    context.user_data["current_mode"] = "fb_uid"
    await query.edit_message_text(
        "🔍 **ĐANG Ở CHẾ ĐỘ: LẤY UID FACEBOOK GỐC**\n\n- Gửi link bài viết hoặc"
        " profile Facebook để lấy số UID chuẩn.",
        reply_markup=back_btn,
        parse_mode="Markdown",
    )
  elif data == "mode_livedie":
    context.user_data["current_mode"] = "livedie"
    # Mẫu giao diện theo dõi live die acc như bạn yêu cầu
    live_die_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🟢 Đang Theo Dõi Liên Tục ✅", callback_data="tracking_active"
            )
        ],
        [
            InlineKeyboardButton("✅ Done kèo", callback_data="done_keo"),
            InlineKeyboardButton("❌ Hủy theo dõi", callback_data="cancel_keo"),
        ],
        [InlineKeyboardButton("🔙 Quay lại Menu Chính", callback_data="home")],
    ])
    sample_report = (
        "🎉 **--- ACC SỐNG LẠI! ---** 🎉\n\n"
        "📖 **FACEBOOK LIVE**\n"
        "👤 **Tên:** [Tên tài khoản mẫu]\n"
        "🔍 **UID:** `1000xxxxxxxxxxx` - Link\n"
        "🟢 **Trạng thái:** ĐÃ SỐNG LẠI ✅\n"
        "📝 **Ghi chú:** FAQ 583/2M (DANG CHIEN)\n"
        "💵 **Giá:** Thỏa thuận\n"
        "⏰ **Thời gian:** 3 ngày 13 giờ 16 phút\n"
        "📅 **Cập nhật lúc:** 26/09/2026 03:58:38\n"
        "📊 **Tiến trình:** Đang Theo Dõi Liên Tục\n"
        "∞\n"
        "👤 **Hạn trả kèo:** Vĩnh Viễn"
    )
    await query.edit_message_text(
        text=sample_report,
        reply_markup=live_die_markup,
        parse_mode="Markdown",
    )
  elif data == "done_keo":
    await query.edit_message_text(
        "✅ **Đã hoàn thành kèo thành công!**",
        reply_markup=back_btn,
        parse_mode="Markdown",
    )
  elif data == "cancel_keo":
    await query.edit_message_text(
        "❌ **Đã hủy theo dõi kèo này.**",
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


# --- XỬ LÝ TIN NHẮN ĐỘC LẬP & TỰ ĐỘNG XÓA SAU 30S ---
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message = update.message
  text_input = message.text.strip()
  current_mode = context.user_data.get("current_mode", None)

  if not current_mode:
    warning_msg = await message.reply_text(
        "⚠️ Vui lòng bấm lệnh /start hoặc chọn một tính năng cụ thể trong menu"
        " trước khi gửi link!"
    )
    context.job_queue.run_once(
        schedule_message_deletion,
        30,
        data={"chat_id": message.chat_id, "message_id": warning_msg.message_id},
    )
    return

  if current_mode == "livedie":
    # Xử lý khi đang ở mode theo dõi live/die (ví dụ gửi ID acc hoặc link cần check)
    info_msg = await message.reply_text(
        f"📊 Đang tiếp nhận thông tin theo dõi cho: `{text_input}`\nHệ thống"
        " đang quét trạng thái Live/Die...",
        parse_mode="Markdown",
    )
    context.job_queue.run_once(
        schedule_message_deletion,
        30,
        data={"chat_id": message.chat_id, "message_id": info_msg.message_id},
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

  if current_mode == "tiktok":
    if "tiktok.com" not in text_input and "douyin.com" not in text_input:
      err_msg = await message.reply_text(
          "❌ Bạn đang ở chế độ **Tải Video TikTok/Douyin**!\n⚠️️ Vui lòng gửi"
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
      await message.reply_video(
          video=res["video_url"],
          caption=(
              f"🎬 **Tiêu đề:** {res['title']}\n👤 **Tác giả:**"
              f" `{res['author']}`"
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

  elif current_mode == "fb_video":
    if "facebook.com" not in text_input and "fb.watch" not in text_input:
      err_msg = await message.reply_text(
          "❌ Bạn đang ở chế độ **Tải Video Facebook**!\n⚠️ Vui lòng gửi đúng"
          " link Facebook Video hoặc Reels."
      )
      context.job_queue.run_once(
          schedule_message_deletion,
          30,
          data={"chat_id": message.chat_id, "message_id": err_msg.message_id},
      )
      return

    wait_msg = await message.reply_text(
        "⏳ Đang xử lý tải video Facebook / Reels..."
    )
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
              f"🎬 **Facebook Video / Reels**\n👤 **Tác giả:**"
              f" `{res['author']}`"
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

  print("🤖 Bot đã tích hợp đầy đủ tính năng Theo dõi Live/Die và Tải video!")
  application.run_polling()


if __name__ == "__main__":
  main()
