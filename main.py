import os
import asyncio
from threading import Thread
from flask import Flask
from pyrogram import Client, filters

# 1. KHỞI TẠO FLASK WEB SERVER (Dành cho Render Free Tier)
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Userbot is running perfectly!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# 2. CẤU HÌNH TỪ BIẾN MÔI TRƯỜNG (ENVIRONMENT VARIABLES)
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "") # Chuỗi Session String thu được từ Pyrogram
TARGET_GROUP = "sendsmsvip"

# Từ điển quản lý các tác vụ đang chạy theo nội dung: {msg_text: asyncio.Task}
active_tasks = {}

# Khởi tạo Client (Sử dụng session_string nếu chạy trên Cloud)
if SESSION_STRING:
    app = Client("my_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
else:
    app = Client("my_account", api_id=API_ID, api_hash=API_HASH)

# Hàm chạy ngầm gửi tin nhắn mỗi 2 phút
async def auto_send_loop(client, chat_id, message_text):
    try:
        while True:
            try:
                await client.send_message(TARGET_GROUP, message_text)
                await client.send_message(chat_id, f"✅ Đã gửi: `{message_text}` vào nhóm @{TARGET_GROUP}")
            except Exception as e:
                await client.send_message(chat_id, f"❌ Lỗi khi gửi `{message_text}`: {e}")
            
            await asyncio.sleep(120) # Chờ 2 phút
    except asyncio.CancelledError:
        pass

# Lệnh bật gửi: .send <nội dung>
@app.on_message(filters.me & filters.command("send", prefixes="."))
async def start_sending(client, message):
    if len(message.command) < 2:
        await message.edit_text("⚠️ Vui lòng nhập nội dung! Ví dụ: `.send /supervip 0941807755`")
        return

    msg_to_send = message.text.split(" ", 1)[1].strip()

    if msg_to_send in active_tasks:
        await message.edit_text(f"⚠️ Nội dung `{msg_to_send}` đang trong tiến trình gửi rồi!")
        return

    # Tạo task chạy ngầm cho tin nhắn này
    task = asyncio.create_task(auto_send_loop(client, message.chat.id, msg_to_send))
    active_tasks[msg_to_send] = task

    await message.edit_text(
        f"🚀 **Đã bật tự động gửi!**\n\n"
        f"📌 **Nội dung:** `{msg_to_send}`\n"
        f"⏱ **Tần suất:** 2 phút / lần\n"
        f"🎯 **Nhóm:** @{TARGET_GROUP}\n\n"
        f"💡 **Cách hủy:**\n"
        f"• Hủy tin nhắn này: `.stop {msg_to_send}`\n"
        f"• Hủy tất cả: `.stop`"
    )

# Lệnh dừng: .stop [nội dung (không bắt buộc)]
@app.on_message(filters.me & filters.command("stop", prefixes="."))
async def stop_sending(client, message):
    if not active_tasks:
        await message.edit_text("⚠️ Hiện tại không có tiến trình nào đang chạy.")
        return

    # Trường hợp truyền cụ thể nội dung cần hủy: .stop /supervip 0941807755
    if len(message.command) > 1:
        target_text = message.text.split(" ", 1)[1].strip()
        
        if target_text in active_tasks:
            active_tasks[target_text].cancel()
            del active_tasks[target_text]
            await message.edit_text(f"🛑 **Đã hủy gửi nội dung:** `{target_text}`")
        else:
            await message.edit_text(f"⚠️ Không tìm thấy tiến trình nào đang gửi nội dung: `{target_text}`")
    
    # Trường hợp gõ duy nhất lệnh .stop -> Dừng tất cả
    else:
        count = len(active_tasks)
        for task in active_tasks.values():
            task.cancel()
        active_tasks.clear()
        await message.edit_text(f"🛑 **Đã dừng toàn bộ ({count}) tiến trình gửi tin nhắn!**")

if __name__ == "__main__":
    # Chạy Web Server Flask trên luồng riêng
    server_thread = Thread(target=run_flask)
    server_thread.daemon = True
    server_thread.start()

    print("Userbot và Flask Server đang hoạt động...")
    app.run()
