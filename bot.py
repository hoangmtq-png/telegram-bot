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

# Khởi tạo Groq Client
groq_client = Groq(api_key=GROQ_API_KEY)

# Cơ sở dữ liệu tạm thời (Thêm trường đếm ngày tiết kiệm)
user_data_db = {}
user_state = {}  # Lưu trạng thái: 'WAITING_INCOME', 'WAITING_EXPENSE', 'CHAT_AI'

# === PHẦN 3: MENU CHÍNH HITECH & TÍCH LŨY TỪNG NGÀY ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data_db:
        user_data_db[user_id] = {
            "daily_income": 0.0, "daily_expense": 0.0,
            "yearly_income": 0.0, "yearly_expense": 0.0,
            "saved_days": 1,  # Khởi tạo mặc định từ 1 ngày tiết kiệm
            "history": []
        }

    d_inc = user_data_db[user_id]["daily_income"]
    d_exp = user_data_db[user_id]["daily_expense"]
    balance = d_inc - d_exp
    saved_days = user_data_db[user_id]["saved_days"]

    # Hiệu ứng thanh tiến trình dòng tiền trực quan
    total_flow = d_inc + d_exp
    if total_flow > 0:
        inc_percent = int((d_inc / total_flow) * 10)
        progress_bar = "🟩" * inc_percent + "🟥" * (10 - inc_percent)
    else:
        progress_bar = "⬛️⬛️⬛️⬛️⬛️⬛️⬛️⬛️⬛️⬛️"

    # Giao diện menu thiết kế dạng thẻ hitech tích hợp số tiền tích lũy và số ngày
    text = (
        "╔═══════════════════════════╗\n"
        "      💎 **H E O  Đ Ấ T  P R O  O S** 💎      \n"
        "╚═══════════════════════════╝\n\n"
        "⚡ **BẢNG ĐIỀU KHIỂN TÀI CHÍNH** ⚡\n"
        f"  📥 **Thu Vào:** `{d_inc:,.0f} đ`\n"
        f"  📤 **Chi Ra:** `{d_exp:,.0f} đ`\n"
        f"  💎 **Số Dư HôM Nay:** `{balance:,.0f} đ`\n\n"
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
            InlineKeyboardButton("🤖 💬 TRỢ LÝ AI LỰA CHỌN", callback_data="chat_ai_mode"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        await update.callback_query.answer()
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# === PHẦN 4: XỬ LÝ NÚT BẤM (CALLBACK QUERY) & XÓA TIN NHẮN GỌN GÀNG ===
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
        await query.message.reply_text("📥 **NHẬP KHOẢN THU:** Vui lòng gửi số tiền (Ví dụ: `500k`, `2tr`, hoặc `500000`):", parse_mode="Markdown")
    elif query.data == "add_expense":
        user_state[user_id] = "WAITING_EXPENSE"
        await query.message.reply_text("📤 **NHẬP KHOẢN CHI:** Vui lòng gửi số tiền (Ví dụ: `50k`, `100000`):", parse_mode="Markdown")
    elif query.data == "chat_ai_mode":
        user_state[user_id] = "CHAT_AI"
        keyboard = [[InlineKeyboardButton("🔙 [ ĐÓNG AI & VỀ MENU CHÍNH ]", callback_data="back_home")]]
        await query.message.edit_text(
            "🚀🤖 **KÍCH HOẠT TRỢ LÝ AI GROQ LLAMA 3** 🤖🚀\n\n"
            "Hệ thống lõi thông minh đã sẵn sàng. Bạn có thể hỏi bất cứ điều gì về tài chính, đầu tư hoặc tâm sự giải trí.\n\n"
            "*(Nhấn nút bên dưới để đóng giao diện chat và làm sạch khung hình)*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
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
        try:
            await query.message.delete()
        except Exception:
            pass
        await start(update, context)

# === PHẦN 5: XỬ LÝ TIN NHẮN & GỌI AI GROQ ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_state:
        user_state[user_id] = "CHAT_AI"

    state = user_state[user_id]

    # TRƯỜNG HỢP 1: ĐANG CHAT VỚI AI
    if state == "CHAT_AI":
        thinking_msg = await update.message.reply_text("🤖 `[AI]` Trợ lý đang xử lý phản hồi...")
        reply_text = ""
        
        prompt_system = (
            "Bạn là một trợ lý tài chính kiêm người bạn thân thiết, vui vẻ, thông minh và hài hước trong một bot Telegram quản lý tài chính cá nhân. "
            "Hãy trò chuyện và tư vấn thật tự nhiên như một con người thực thụ, đôi khi dùng emoji sinh động, trả lời súc tích và hữu ích."
        )

        try:
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=1024,
            )
            reply_text = completion.choices[0].message.content
        except Exception as e:
            logging.error(f"Lỗi Groq AI: {e}")
            reply_text = "⚠️ Hệ thống AI đang bận chút xíu do lượng truy cập, bạn nhắn lại giúp mình nhé!"

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=thinking_msg.message_id,
            text=f"🤖 **Trợ Lý AI:**\n\n{reply_text}",
            parse_mode="Markdown"
        )
        return

    # TRƯỜNG HỢP 2 & 3: ĐANG NHẬP THU NHẬP HOẶC CHI TIÊU
    try:
        clean_text = text.lower().replace("vnđ", "").replace("đ", "").replace("d", "").replace(",", "").replace(".", "").strip()
        if "k" in clean_text:
            amount = float(clean_text.replace("k", "")) * 1000
        elif "tr" in clean_text:
            amount = float(clean_text.replace("tr", "")) * 1000000
        else:
            amount = float(clean_text)
    except ValueError:
        await update.message.reply_text("❌ Định dạng số tiền không hợp lệ. Vui lòng nhập lại rõ ràng (Ví dụ: `50k`, `2tr`, hoặc `100000`).")
        return

    current_time = datetime.now().strftime("%H:%M")

    if state == "WAITING_INCOME":
        user_data_db[user_id]["daily_income"] += amount
        user_data_db[user_id]["yearly_income"] += amount
        user_data_db[user_id]["history"].append({"time": current_time, "type": "Thu", "amount": amount})
        await update.message.reply_text(f"✅ Nạp quỹ thành công: `+{amount:,.0f} đ` vào **Thu Nhập**! 🐷💰", parse_mode="Markdown")
        
    elif state == "WAITING_EXPENSE":
        user_data_db[user_id]["daily_expense"] += amount
        user_data_db[user_id]["yearly_expense"] += amount
        user_data_db[user_id]["history"].append({"time": current_time, "type": "Chi", "amount": amount})
        await update.message.reply_text(f"✅ Ghi nhận giao dịch: `-{amount:,.0f} đ` vào **Chi Tiêu**! 💸", parse_mode="Markdown")

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
        
        # Reset số liệu ngày cũ nhưng cộng dồn ngày tiết kiệm lên
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
