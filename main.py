import os
import sys
import json
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

TARGET_GROUP = "@sendsmsvip"
active_tasks = {}
DATA_FILE = "tasks_data.json"

# Khởi tạo Client
app = Client("my_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# --- QUẢN LÝ TỰ ĐỘNG LƯU TRẠNG THÁI TASK ---
def save_tasks_to_file():
    """Lưu danh sách tác vụ đang chạy vào file json để không bị mất khi Render restart"""
    try:
        tasks_data = {msg_text: chat_id for msg_text, (_, chat_id) in active_tasks.items()}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks_data, f, ensure_ascii=False)
    except Exception as e:
        print(f"Lỗi lưu file: {e}")

def load_tasks_from_file():
    """Đọc danh sách tác vụ từ file json khi khởi động lại"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Lỗi đọc file: {e}")
    return {}

# --- HÀM XÓA TIN NHẮN TỰ ĐỘNG ---
async def delete_msg_after_30s(msg):
    await asyncio.sleep(30)
    try:
        await msg.delete()
    except Exception:
        pass

# --- VÒNG LẶP GỬI TIN NHẮN ---
async def auto_send_loop(client, chat_id, message_text):
    # Tự động join nhóm trước nếu chưa join
    try:
        await client.join_chat(TARGET_GROUP)
    except Exception:
        pass

    try:
        while True:
            try:
                # 1. Gửi tin nhắn vào nhóm mục tiêu
                await client.send_message(TARGET_GROUP, message_text)
                
                # 2. Gửi thông báo báo cáo vào ô chat
                status_msg = await client.send_message(chat_id, f"✅ Đã gửi: `{message_text}` vào nhóm {TARGET_GROUP}")
                
                # 3. Tự động xóa báo cáo sau 30 giây
                asyncio.create_task(delete_msg_after_30s(status_msg))

            except Exception as e:
                error_msg = await client.send_message(chat_id, f"❌ Lỗi gửi vào {TARGET_GROUP}: `{e}`")
                asyncio.create_task(delete_msg_after_30s(error_msg))
            
            # Đợi 60 giây (1 phút) cho lần gửi tiếp theo
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        pass

# --- LỆNH BẬT GỬI: .send <nội dung> ---
@app.on_message(filters.me & filters.command("send", prefixes="."))
async def start_sending(client, message):
    if len(message.command) < 2:
        await message.edit_text("⚠️ Vui lòng nhập nội dung! Ví dụ: `.send /supervip 0941807755`")
        return

    msg_to_send = message.text.split(" ", 1)[1].strip()

    if msg_to_send in active_tasks:
        await message.edit_text(f"⚠️ Nội dung `{msg_to_send}` đang chạy rồi!")
        return

    # Tạo tác vụ gửi tự động
    task = asyncio.create_task(auto_send_loop(client, message.chat.id, msg_to_send))
    active_tasks[msg_to_send] = (task, message.chat.id)
    save_tasks_to_file()

    await message.edit_text(
        f"🚀 **Đã bật tự động gửi liên tục!**\n\n"
        f"📌 **Nội dung:** `{msg_to_send}`\n"
        f"⏱ **Tần suất:** 1 phút / lần\n"
        f"🎯 **Nhóm:** {TARGET_GROUP}\n\n"
        f"💡 **Chỉ dừng khi gõ:** `.stop {msg_to_send}` hoặc `.stop`"
    )

# --- LỆNH DỪNG: .stop [nội dung] ---
@app.on_message(filters.me & filters.command("stop", prefixes="."))
async def stop_sending(client, message):
    if not active_tasks:
        await message.edit_text("⚠️ Không có tiến trình nào đang chạy.")
        return

    if len(message.command) > 1:
        target_text = message.text.split(" ", 1)[1].strip()
        if target_text in active_tasks:
            task, _ = active_tasks[target_text]
            task.cancel()
            del active_tasks[target_text]
            save_tasks_to_file()
            await message.edit_text(f"🛑 **Đã dừng gửi nội dung:** `{target_text}`")
        else:
            await message.edit_text(f"⚠️ Không tìm thấy tiến trình: `{target_text}`")
    else:
        for task, _ in active_tasks.values():
            task.cancel()
        active_tasks.clear()
        save_tasks_to_file()
        await message.edit_text("🛑 **Đã dừng toàn bộ tiến trình gửi tự động!**")

# --- CHẠY TIẾN TRÌNH CHÍNH & KHÔI PHỤC LẠI TASK KHI BOT KHỞI ĐỘNG ---
async def main():
    Thread(target=run_flask, daemon=True).start()
    await app.start()
    print("✅ Userbot & Flask Web Server đã sẵn sàng!")

    # Khôi phục các lệnh gửi đang chạy dở (nếu Render vừa khởi động lại)
    saved_tasks = load_tasks_from_file()
    for msg_text, chat_id in saved_tasks.items():
        task = asyncio.create_task(auto_send_loop(app, chat_id, msg_text))
        active_tasks[msg_text] = (task, chat_id)
        print(f"🔄 Đã khôi phục tác vụ gửi: {msg_text}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    loop.run_until_complete(main())
