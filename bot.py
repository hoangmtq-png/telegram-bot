# === TOÀN BỘ CODE HOÀN CHỈNH: BOT HEO ĐẤT AI (GROQ) ===
import os
import time
import logging
from datetime import datetime
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from groq import Groq

# Cấu hình logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# === PHẦN 1: FLASK SERVER GIỮ BOT SỐNG TRÊN RENDER ===
app = Flask('')

@app.route('/')
def home():
    return "Bot Heo Đất AI đang hoạt động 24/7 ngon lành!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# === PHẦN 2: CẤU HÌNH TOKEN VÀ AI (GROQ - LLAMA 3) ===
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "THAY_TOKEN_TELEGRAM_VÀO_ĐÂY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "THAY_API_KEY_GROQ_VÀO_ĐÂY")

groq_client = Groq(api_key=GROQ_API_KEY)

user_data_db = {}
user_state = {}  
user_chat_histories = {} 
user_ai_messages = {}
user_all_chat_msg_ids = {} # Lưu toàn bộ tin nhắn trong phiên chat AI để xóa khi đóng

# === PHẦN 3: HÀM TẠO GIAO DIỆN MENU CHÍNH ===
def get_main_menu_content(user_id):
    if user_id not in user_data_db:
        user_data_db[user_id] = {
            "daily_income": 0.0, "daily_expense": 0.0,
            "yearly_income": 0.0, "yearly_expense": 0.0,
            "saved_days": 1,
            "history": []
        }

    d_inc = user_data_db[user_id]["daily_income"]
    d_exp = user_data_db[user_id]["daily_expense"]
    balance = d_inc - d_exp
    saved_days = user_data_db[user_id]["saved_days"]

    total_flow = d_inc + d_exp
    if total_flow > 0:
        inc_percent = int((d_inc / total_flow) * 10)
        progress_bar = "🟢" * inc_percent + "🔴" * (10 - inc_percent)
    else:
        progress_bar = "⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️"

    text = (
        "╔═══════════════════════════╗\n"
        "      💎 **H E O  Đ Ấ T  P R O  O S** 💎      \n"
        "╚═══════════════════════════╝\n\n"
        "⚡ **BẢNG ĐIỀU KHIỂN TÀI CHÍNH** ⚡\n"
        f"  📥 **Thu Vào:** `{d_inc:,.0f} đ`\n"
        f"  📤 **Chi Ra:** `{d_exp:,.0f} đ`\n"
        f"  💎 **Số Dư Hôm Nay:** `{balance:,.0f} đ`\n\n"
        f"📊 **Dòng Tiền:**\n`[{progress_bar}]`\n\n"
        f"💰 **Tích lũy thực tế:** Đã cất dành được `{balance:,.0f} đ` qua **{saved_days} ngày** (đã trừ hết các khoản chi)!\n\n"
        "🔥 *Lựa chọn tác vụ phía dưới để tiếp tục:*"
    )

    keyboard = [
        [
            InlineKeyboardButton("➕ 📥 NẠP THU", callback_data="add_income"),
            InlineKeyboardButton("➖ 📤 RÚT CHI", callback_data="add_expense"),
        ],
        [
            InlineKeyboardButton("📜 SỔ GIAO DỊCH", callback_data="view_history"),
            InlineKeyboardButton("📈 TỔNG KẾT NĂM", callback_data="view_year"),
        ],
        [
            InlineKeyboardButton("🤖 💬 HEO ĐẤT AI ĐA NĂNG", callback_data="chat_ai_mode"),
        ]
    ]
    return text, InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text, reply_markup = get_main_menu_content(user_id)

    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        await update.callback_query.answer()
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# === PHẦN 4: XỬ LÝ NÚT BẤM (CALLBACK QUERY) ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_data_db:
        user_data_db[user_id] = {
            "daily_income": 0.0, "daily_expense": 0.0,
            "yearly_income": 0.0, "yearly_expense": 0.0,
            "saved_days": 1,
            "history": []
        }

    if query.data == "add_income":
        user_state[user_id] = "WAITING_INCOME"
        msg = await query.message.reply_text("📥 **NHẬP KHOẢN THU:** Vui lòng gửi số tiền (Ví dụ: `500k`, `2tr`, hoặc `500000`):", parse_mode="Markdown")
        user_ai_messages[user_id] = [msg.message_id]
    elif query.data == "add_expense":
        user_state[user_id] = "WAITING_EXPENSE"
        msg = await query.message.reply_text("📤 **NHẬP KHOẢN CHI:** Vui lòng gửi số tiền (Ví dụ: `50k`, `100000`):", parse_mode="Markdown")
        user_ai_messages[user_id] = [msg.message_id]
    elif query.data == "chat_ai_mode":
        user_state[user_id] = "CHAT_AI"
        user_all_chat_msg_ids[user_id] = [] # Khởi tạo danh sách lưu tin nhắn trong phiên chat AI
        
        keyboard = [[InlineKeyboardButton("🔙 [ ĐÓNG AI & VỀ MENU CHÍNH ]", callback_data="back_home")]]
        intro_msg = await query.message.reply_text(
            "🚀🤖 **KÍCH HOẠT HEO ĐẤT AI ĐA NĂNG** 🤖🚀\n\n"
            "Mình là Heo Đất AI siêu cấp đa năng! Bạn có thể yêu cầu mình tìm hình ảnh, link phim, tra cứu thông tin, giải đáp mọi thắc mắc hoặc quản lý tài chính.\n\n"
            "💡 *Mẹo: Bạn có thể chat trực tiếp hoặc gõ 'đóng khung chat' / bấm nút bên dưới để đóng và dọn sạch tin nhắn.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        user_all_chat_msg_ids[user_id].append(intro_msg.message_id)
        
        # Xóa tin nhắn menu cũ đi để khung chat AI gọn gàng độc lập
        try:
            await query.message.delete()
        except Exception:
            pass

    elif query.data == "view_history":
        history = user_data_db[user_id]["history"][-5:]
        if not history:
            history_text = "✨ *Chưa ghi nhận giao dịch nào trong ngày.*"
        else:
            history_text = "\n".join([f"🔹 `[{h['time']}]` **{h['type']}**: `{h['amount']:,.0f} đ`" for h in history])
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")]]
        await query.message.edit_text(
            f"📜 **5 GIAO DỊCH GẦN NHẤT HÔM NAY**\n\n{history_text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    elif query.data == "view_year":
        y_inc = user_data_db[user_id]["yearly_income"]
        y_exp = user_data_db[user_id]["yearly_expense"]
        y_balance = y_inc - y_exp
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")]]
        await query.message.edit_text(
            f"📈 **BÁO CÁO TÀI CHÍNH TOÀN NĂM** 📈\n\n"
            f"🟢 Tổng Thu Tích Lũy: `{y_inc:,.0f} đ`\n"
            f"🔴 Tổng Chi Tiêu: `{y_exp:,.0f} đ`\n"
            f"💎 **Số Dư Thực Tế:** `{y_balance:,.0f} đ`\n\n"
            f"🎯 *Dữ liệu đã được mã hóa an toàn!*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    elif query.data == "back_home":
        user_state.pop(user_id, None)
        if user_id in user_chat_histories:
            user_chat_histories[user_id] = []
        
        # Xóa toàn bộ tin nhắn đã trao đổi trong khung chat AI khi bấm nút đóng
        if user_id in user_all_chat_msg_ids:
            for msg_id in user_all_chat_msg_ids[user_id]:
                try:
                    await context.bot.delete_message(chat_id=query.message.chat_id, message_id=msg_id)
                except Exception:
                    pass
            user_all_chat_msg_ids[user_id] = []

        if user_id in user_ai_messages:
            for msg_id in user_ai_messages[user_id]:
                try:
                    await context.bot.delete_message(chat_id=query.message.chat_id, message_id=msg_id)
                except Exception:
                    pass
            user_ai_messages[user_id] = []

        try:
            await query.message.delete()
        except Exception:
            pass
        
        text, reply_markup = get_main_menu_content(user_id)
        await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")

# === PHẦN 5: XỬ LÝ TIN NHẮN & TÍNH NĂNG ĐÓNG KHUNG CHAT BẰNG LỜI NÓI ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if user_id not in user_state:
        user_state[user_id] = "CHAT_AI"

    state = user_state[user_id]

    if state == "CHAT_AI":
        # 1. Kiểm tra nếu người dùng yêu cầu đóng khung chat bằng lời nói
        close_keywords = ["đóng khung chat", "đóng chat", "thoát ai", "về menu", "đóng lại"]
        if any(keyword in text.lower() for keyword in close_keywords):
            # Xóa tin nhắn yêu cầu đóng của người dùng
            try:
                await update.message.delete()
            except Exception:
                pass

            # Xóa toàn bộ lịch sử tin nhắn trong khung chat AI
            if user_id in user_all_chat_msg_ids:
                for msg_id in user_all_chat_msg_ids[user_id]:
                    try:
                        await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    except Exception:
                        pass
                user_all_chat_msg_ids[user_id] = []

            user_state.pop(user_id, None)
            if user_id in user_chat_histories:
                user_chat_histories[user_id] = []

            # Hiện lại menu chính sạch sẽ
            text_menu, reply_markup = get_main_menu_content(user_id)
            await context.bot.send_message(chat_id=chat_id, text=text_menu, reply_markup=reply_markup, parse_mode="Markdown")
            return

        # 2. Xử lý chat AI bình thường
        try:
            user_msg_id = update.message.message_id
            if user_id not in user_all_chat_msg_ids:
                user_all_chat_msg_ids[user_id] = []
            user_all_chat_msg_ids[user_id].append(user_msg_id)
            
            # Xóa ngay tin nhắn câu hỏi của user để khung chat luôn gọn chỉ hiển thị câu trả lời của AI (hoặc giữ lại tùy ý, ở đây code đang xóa tin nhắn user và hiển thị câu trả lời)
            await update.message.delete()
        except Exception:
            pass

        thinking_msg = await context.bot.send_message(chat_id=chat_id, text="🐷 Heo Đất AI đang trả lời...")
        user_all_chat_msg_ids[user_id].append(thinking_msg.message_id)

        now = datetime.now()
        current_time_str = now.strftime("%H:%M:%S, Ngày %d/%m/%Y")
        days_vn = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        current_weekday = days_vn[now.weekday()]

        prompt_system = (
            f"Hôm nay là {current_weekday}, {current_time_str}. "
            "Bạn tên là Heo Đất AI, trợ lý thông minh đa năng. "
            "Hãy lưu ý rằng bạn là mô hình ngôn ngữ AI, không có khả năng tự động tra cứu dữ liệu thời gian thực hay số điện thoại cá nhân trên mạng để bảo mật thông tin. "
            "Hãy trả lời thông minh, thân thiện và rõ ràng."
        )

        if user_id not in user_chat_histories:
            user_chat_histories[user_id] = []

        user_chat_histories[user_id].append({"role": "user", "content": text})
        
        if len(user_chat_histories[user_id]) > 10:
            user_chat_histories[user_id] = user_chat_histories[user_id][-10:]

        try:
            messages = [{"role": "system", "content": prompt_system}] + user_chat_histories[user_id]
            
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            reply_text = completion.choices[0].message.content
            
            user_chat_histories[user_id].append({"role": "assistant", "content": reply_text})

        except Exception as e:
            logging.error(f"Lỗi Groq AI: {e}")
            reply_text = "⚠️ Hệ thống AI đang bận chút xíu, bạn nhắn lại giúp mình nhé!"

        # Xóa thông báo "đang trả lời" và gửi câu trả lời hoàn chỉnh
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=thinking_msg.message_id)
            user_all_chat_msg_ids[user_id].remove(thinking_msg.message_id)
        except Exception:
            pass

        bot_reply_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"🐷 **Heo Đất AI:**\n\n{reply_text}",
            parse_mode="Markdown"
        )
        user_all_chat_msg_ids[user_id].append(bot_reply_msg.message_id)
        return

    # XỬ LÝ NHẬP TIỀN THU / CHI
    try:
        clean_text = text.lower().replace("vnđ", "").replace("đ", "").replace("d", "").replace(",", "").replace(".", "").strip()
        if "k" in clean_text:
            amount = float(clean_text.replace("k", "")) * 1000
        elif "tr" in clean_text:
            amount = float(clean_text.replace("tr", "")) * 1000000
        else:
            amount = float(clean_text)
    except ValueError:
        try:
            await update.message.delete()
        except Exception:
            pass
        err_msg = await context.bot.send_message(chat_id=chat_id, text="❌ Định dạng số tiền không hợp lệ. Vui lòng nhập lại rõ ràng (Ví dụ: `50k`, `2tr`, hoặc `100000`).", parse_mode="Markdown")
        user_ai_messages[user_id] = [err_msg.message_id]
        return

    if user_id in user_ai_messages:
        for msg_id in user_ai_messages[user_id]:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception:
                pass
        user_ai_messages[user_id] = []

    try:
        await update.message.delete()
    except Exception:
        pass

    current_time = datetime.now().strftime("%H:%M")

    if state == "WAITING_INCOME":
        user_data_db[user_id]["daily_income"] += amount
        user_data_db[user_id]["yearly_income"] += amount
        user_data_db[user_id]["history"].append({"time": current_time, "type": "Thu", "amount": amount})
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Nạp quỹ thành công: `+{amount:,.0f} đ` vào **Thu Nhập**! 🐷💰", parse_mode="Markdown")
        
    elif state == "WAITING_EXPENSE":
        user_data_db[user_id]["daily_expense"] += amount
        user_data_db[user_id]["yearly_expense"] += amount
        user_data_db[user_id]["history"].append({"time": current_time, "type": "Chi", "amount": amount})
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Ghi nhận giao dịch: `-{amount:,.0f} đ` vào **Chi Tiêu**! 💸", parse_mode="Markdown")

    user_state.pop(user_id, None)

# === PHẦN 6: TỰ ĐỘNG CHỐT SỔ ĐÊM & TĂNG SỐ NGÀY TÍCH LŨY ===
async def send_daily_report(application):
    current_date = datetime.now().strftime("%d/%m/%Y")
    for user_id, data in user_data_db.items():
        inc = data["daily_income"]
        exp = data["daily_expense"]
        balance = inc - exp
        
        report_text = (
            f"🌙 **BÁO CÁO TÀI CHÍNH CUỐI NGÀY ({current_date})** 🌙\n\n"
            f"🟢 Tổng thu hôm nay: `{inc:,.0f} đ`\n"
            f"🔴 Tổng chi hôm nay: `{exp:,.0f} đ`\n"
            f"💰 Số dư chốt sổ ngày: `{balance:,.0f} đ`\n\n"
            f"🍀 Chúc bạn có một giấc ngủ thật ngon, ngày mai đón tài lộc bội thu nhé! 🚀✨"
        )
        try:
            await application.bot.send_message(chat_id=user_id, text=report_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Lỗi gửi báo cáo ngày cho {user_id}: {e}")
        
        data["daily_income"] = 0.0
        data["daily_expense"] = 0.0
        data["saved_days"] += 1
        data["history"] = []

async def send_yearly_report(application):
    current_year = datetime.now().strftime("%Y")
    for user_id, data in user_data_db.items():
        y_inc = data["yearly_income"]
        y_exp = data["yearly_expense"]
        y_balance = y_inc - y_exp
        
        report_text = (
            f"🎉🎆 **TỔNG KẾT TÀI CHÍNH TOÀN BỘ NĂM {current_year}** 🎆🎉\n\n"
            f"🎯 Thành quả tuyệt vời của bạn trong năm qua:\n"
            f"🟢 Tổng thu cả năm: `{y_inc:,.0f} đ`\n"
            f"🔴 Tổng chi cả năm: `{y_exp:,.0f} đ`\n"
            f"💰 Tổng dư tích lũy: `{y_balance:,.0f} đ`\n\n"
            f"🏆 Chúc mừng bạn đã xuất sắc! Chào đón năm mới tiền tài như nước! 🚀🧧"
        )
        try:
            await application.bot.send_message(chat_id=user_id, text=report_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Lỗi gửi báo cáo năm cho {user_id}: {e}")
            
        data["yearly_income"] = 0.0
        data["yearly_expense"] = 0.0
        data["saved_days"] = 1

def schedule_jobs(application):
    scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
    # Cấu hình lịch tự động chạy lúc 00:00 mỗi ngày
    scheduler.add_job(lambda: application.create_task(send_daily_report(application)), 'cron', hour=0, minute=0)
    scheduler.add_job(lambda: application.create_task(send_yearly_report(application)), 'cron', month=12, day=31, hour=0, minute=0)
    scheduler.start()

# === PHẦN 7: KHỞI CHẠY HỆ THỐNG ===
def main():
    keep_alive()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    schedule_jobs(application)

    logging.info("Bot Heo Đất AI (Groq) đang chạy mượt mà...")
    application.run_polling()

if __name__ == "__main__":
    main()
