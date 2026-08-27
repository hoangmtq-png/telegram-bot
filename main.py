import os
import asyncio
from threading import Thread
from flask import Flask
from pyrogram import Client, filters

# 1. KHỞI TẠO FLASK ĐỂ RENDER KIỂM TRA HEALTH CHECK (DUY TRÌ SỐNG)
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Userbot đang hoạt động 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# 2. KHỞI TẠO BOT VỚI EVENT LOOP SỬA LỖI PYTHON 3.14
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
TARGET_GROUP = "sendsmsvip"

active_tasks = {}

# Khai báo Client
app = Client("my_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Hàm gửi tin lặp lại
async def auto_send_loop(client, chat_id, message_text):
    try:
        while True:
            try:
                await client.send_message(TARGET_GROUP, message_text)
                await client.send_message(chat_id, f"✅ Đã gửi: `{message_text}` vào nhóm @{TARGET_GROUP}")
            except Exception as e:
                await client.send_message(chat_id, f"❌ Lỗi gửi `{message_text}`: {e}")
            await asyncio.sleep(120)
    except asyncio.CancelledError:
        pass

# Lệnh bật gửi tin
@app.on_message(filters.me & filters.command("send", prefixes="."))
async def start_sending(client, message):
    if len(message.command) < 2:
        await message.edit_text("⚠️ Vui lòng nhập nội dung! Ví dụ: `.send /supervip 0941807755`")
        return

    msg_to_send = message.text.split(" ", 1)[1].strip()

    if msg_to_send in active_tasks:
        await message.edit_text(f"⚠️ Nội dung `{msg_to_send}` đang chạy rồi!")
        return

    task = asyncio.create_task(auto_send_loop(client, message.chat.id, msg_to_send))
    active_tasks[msg_to_send] = task

    await message.edit_text(
        f"🚀 **Đã bật tự động gửi!**\n\n"
        f"📌 **Nội dung:** `{msg_to_send}`\n"
        f"⏱ **Tần suất:** 2 phút / lần\n"
        f"🎯 **Nhóm:** @{TARGET_GROUP}\n\n"
        f"💡 **Hủy gửi:** Gõ `.stop {msg_to_send}` hoặc `.stop` để hủy tất cả."
    )

# Lệnh dừng gửi
@app.on_message(filters.me & filters.command("stop", prefixes="."))
async def stop_sending(client, message):
    if not active_tasks:
        await message.edit_text("⚠️ Không có tiến trình nào đang chạy.")
        return

    if len(message.command) > 1:
        target_text = message.text.split(" ", 1)[1].strip()
        if target_text in active_tasks:
            active_tasks[target_text].cancel()
            del active_tasks[target_text]
            await message.edit_text(f"🛑 **Đã hủy nội dung:** `{target_text}`")
        else:
            await message.edit_text(f"⚠️ Không tìm thấy tiến trình: `{target_text}`")
    else:
        for task in active_tasks.values():
            task.cancel()
        active_tasks.clear()
        await message.edit_text("🛑 **Đã dừng tất cả các tiến trình!**")

# 3. HÀM CHẠY CHÍNH (SỬA LỖI RUNTIMEERROR EVENT LOOP)
async def main():
    # Bật server Flask ở luồng riêng
    server_thread = Thread(target=run_flask, daemon=True)
    server_thread.start()

    # Bật Pyrogram Client
    await app.start()
    print("Userbot và Flask Server đã kết nối thành công!")
    await asyncio.Event().wait() # Giữ tiến trình chạy ngầm vĩnh viễn

if __name__ == "__main__":
    asyncio.run(main())
