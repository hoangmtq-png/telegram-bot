import os
import sys
import asyncio
from threading import Thread
from flask import Flask
from hydrogram import Client, filters

# 1. TẠO EVENT LOOP TRƯỚC ĐỂ TRÁNH LỖI PYTHON 3.14
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# 2. KHỞI TẠO FLASK WEB SERVER (Health Check Render)
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Userbot Status: Running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# 3. ĐỌC BIẾN MÔI TRƯỜNG
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

if not API_ID or not API_HASH or not SESSION_STRING:
    print("❌ LỖI: Thiếu API_ID, API_HASH hoặc SESSION_STRING trong Environment Variables!")
    sys.exit(1)

# Nhóm mục tiêu (bắt buộc có dấu @ ở đầu)
TARGET_GROUP = "@sendsmsvip"
active_tasks = {}

# Khởi tạo Client
app = Client("my_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Hàm phụ trợ xóa tin nhắn sau 30 giây
async def delete_msg_after_30s(msg):
    await asyncio.sleep(30)
    try:
        await msg.delete()
    except Exception:
        pass

# Vòng lặp gửi tin nhắn tự động (1 phút/lần)
async def auto_send_loop(client, chat_id, message_text):
    # Tự động gia nhập nhóm trước để tránh lỗi chưa join chat
    try:
        await client.join_chat(TARGET_GROUP)
    except Exception:
        pass

    try:
        while True:
            try:
                # Gửi tin vào nhóm mục tiêu
                await client.send_message(TARGET_GROUP, message_text)
                
                # Gửi báo cáo thành công vào ô chat
                status_msg = await client.send_message(chat_id, f"✅ Đã gửi: `{message_text}` vào nhóm {TARGET_GROUP}")
                
                # Tự động xóa báo cáo thành công sau 30 giây
                asyncio.create_task(delete_msg_after_30s(status_msg))

            except Exception as e:
                # Nếu có lỗi (chặn chat, slowmode,...), gửi thông báo lỗi chi tiết
                error_msg = await client.send_message(chat_id, f"❌ Lỗi gửi vào {TARGET_GROUP}: `{e}`")
                asyncio.create_task(delete_msg_after_30s(error_msg))
            
            # Chờ 60 giây (1 phút) cho lần gửi tiếp theo
            await asyncio.sleep(60)
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
        await message.edit_text(f"⚠️ Nội dung `{msg_to_send}` đang chạy rồi!")
        return

    task = asyncio.create_task(auto_send_loop(client, message.chat.id, msg_to_send))
    active_tasks[msg_to_send] = task

    # Tin nhắn này GIỮ NGUYÊN trong chat (không xóa)
    await message.edit_text(
        f"🚀 **Đã bật tự động gửi!**\n\n"
        f"📌 **Nội dung:** `{msg_to_send}`\n"
        f"⏱ **Tần suất:** 1 phút / lần\n"
        f"🎯 **Nhóm:** {TARGET_GROUP}\n\n"
        f"💡 **Hủy gửi:** Gõ `.stop {msg_to_send}` hoặc `.stop` để dừng tất cả."
    )

# Lệnh dừng: .stop [nội dung]
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
        await message.edit_text("🛑 **Đã dừng toàn bộ tiến trình!**")

# 4. CHẠY TIẾN TRÌNH CHÍNH
async def main():
    Thread(target=run_flask, daemon=True).start()
    await app.start()
    print("✅ Userbot & Flask Web Server đã sẵn sàng!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop.run_until_complete(main())
