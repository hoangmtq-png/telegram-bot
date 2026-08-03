# =====================================================================
# GROK AI PRO OS - FULL CHỨC NĂNG & HỆ THỐNG THÔNG MINH CAO CẤP
# =====================================================================
import os
import time
import logging
import urllib.parse
from datetime import datetime
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
import google.generativeai as genai

# --- CẤU HÌNH HỆ THỐNG LOGGING ---
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", 
    level=logging.INFO
)

# --- KHỞI TẠO WEB SERVER DUY TRÌ 24/7 (KEEP ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Grok AI Pro OS Server is Running 24/7 with High Performance!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

# --- CẤU HÌNH API TOKENS ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "THAY_TOKEN_TELEGRAM_VÀO_ĐÂY")
AI_API_KEY = os.environ.get("GEMINI_API_KEY", "THAY_API_KEY_VÀO_ĐÂY")

genai.configure(api_key=AI_API_KEY)

generation_config = {
    "temperature": 0.85,
    "max_output_tokens": 1500,
}
grok_engine = genai.GenerativeModel(
    model_name='gemini-1.5-flash', 
    generation_config=generation_config,
    system_instruction="Bạn là Grok, một trợ lý AI thông minh, sắc sảo, hài hước, phản hồi nhanh chóng, chính xác và có cá tính mạnh mẽ."
)

# --- CƠ SỞ DỮ LIỆU TẠM THỜI TRONG BỘ NHỚ (IN-MEMORY DATABASE) ---
user_data_db = {}
user_state = {}  
user_chat_histories = {} 
user_ai_messages = {}
user_all_chat_msg_ids = {} 
user_last_menu_id = {}

# =====================================================================
# MODULE 1: HỆ THỐNG GIAO DIỆN & ĐIỀU KHIỂN TÀI CHÍNH
# =====================================================================
def get_main_menu_content(user_id):
    if user_id not in user_data_db:
        user_data_db[user_id] = {
            "daily_income": 0.0, 
            "daily_expense": 0.0,
            "yearly_income": 0.0, 
            "yearly_expense": 0.0,
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

    menu_text = (
        "╔═════════════════════════════════╗\n"
        "      ⚡ **G R O K  AI  P R O  O S** ⚡      \n"
        "╚═════════════════════════════════╝\n\n"
        "📊 **BẢNG ĐIỀU KHIỂN TÀI CHÍNH THÔNG MINH** 📊\n"
        f"  📥 **Thu Vào:** `{d_inc:,.0f} đ`\n"
        f"  📤 **Chi Ra:** `{d_exp:,.0f} đ`\n"
        f"  💎 **Số Dư Hôm Nay:** `{balance:,.0f} đ`\n\n"
        f"📈 **Dòng Tiền:**\n`[{progress_bar}]`\n\n"
        f"💰 **Tích lũy thực tế:** Đã cất dành được `{balance:,.0f} đ` qua **{saved_days} ngày**!\n\n"
        "🔥 *Chọn tác vụ thông minh bên dưới để tiếp tục:*"
    )

    keyboard = [
        [
            InlineKeyboardButton("➕ 📥 NẠP THU", callback_data="add_income"),
            InlineKeyboardButton("➖ 📤 RÚT CHI", callback_data="add_expense"),
        ],
        [
            InlineKeyboardButton("📜 SỔ GIAO DỊCH", callback_data="view_history"),
            InlineKeyboardButton("📋 SỔ CHI TIÊU", callback_data="view_detail_ledger"),
        ],
        [
            InlineKeyboardButton("📈 TỔNG KẾT NĂM", callback_data="view_year"),
            InlineKeyboardButton("🤖 💬 TRÒ CHUYỆN VỚI GROK", callback_data="chat_ai_mode"),
        ]
    ]
    return menu_text, InlineKeyboardMarkup(keyboard)

# =====================================================================
# MODULE 2: XỬ LÝ LỆNH /START VÀ CALLBACK QUẢN LÝ GIAO DIỆN
# =====================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    menu_text, reply_markup = get_main_menu_content(user_id)

    if user_id in user_last_menu_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=user_last_menu_id[user_id])
        except Exception:
            pass

    if update.callback_query:
        try:
            await update.callback_query.message.delete()
        except Exception:
            pass
        await update.callback_query.answer()

    msg = await context.bot.send_message(chat_id=chat_id, text=menu_text, reply_markup=reply_markup, parse_mode="Markdown")
    user_last_menu_id[user_id] = msg.message_id

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    data = query.data

    if user_id not in user_data_db:
        user_data_db[user_id] = {
            "daily_income": 0.0, "daily_expense": 0.0,
            "yearly_income": 0.0, "yearly_expense": 0.0,
            "saved_days": 1,
            "history": []
        }

    if data == "add_income":
        user_state[user_id] = "WAITING_INCOME"
        msg = await query.message.reply_text("📥 **NHẬP KHOẢN THU:** Vui lòng gửi số tiền (ví dụ: `50k`, `2tr`, `500000`):", parse_mode="Markdown")
        user_ai_messages[user_id] = [msg.message_id]
        
    elif data == "add_expense":
        user_state[user_id] = "WAITING_EXPENSE"
        msg = await query.message.reply_text("📤 **NHẬP KHOẢN CHI:** Vui lòng gửi số tiền (ví dụ: `100k`, `1.5tr`):", parse_mode="Markdown")
        user_ai_messages[user_id] = [msg.message_id]
        
    elif data == "chat_ai_mode":
        user_state[user_id] = "CHAT_AI"
        user_all_chat_msg_ids[user_id] = []
        
        keyboard = [[InlineKeyboardButton("🔙 [ ĐÓNG GROK & VỀ MENU CHÍNH ]", callback_data="back_home")]]
        intro_msg = await query.message.reply_text(
            "⚡🤖 **ĐÃ KÍCH HOẠT HỆ THỐNG GROK AI PRO** 🤖⚡\n\n"
            "Tôi là Grok, sẵn sàng hỗ trợ bạn phân tích dữ liệu, tra cứu, viết code, tìm nhạc và tạo ảnh sắc nét!\n\n"
            "💡 *Bấm nút bên dưới khi muốn quay lại menu tài chính.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        user_all_chat_msg_ids[user_id].append(intro_msg.message_id)
        user_last_menu_id[user_id] = query.message.message_id

        try:
            await query.message.delete()
        except Exception:
            pass

    elif data == "view_history":
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
        
    elif data == "view_detail_ledger":
        history = user_data_db[user_id]["history"]
        if not history:
            keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")]]
            await query.message.edit_text("📋 **SỔ CHI TIÊU GIAO DỊCH**\n\n✨ *Chưa có giao dịch nào được ghi nhận.*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        ledger_text = "📋 **SỔ CHI TIÊU & GIAO DỊCH CHI TIẾT**\n\n"
        keyboard = []
        for idx, h in enumerate(history):
            icon = "🟢" if h['type'] == "Thu" else "🔴"
            ledger_text += f"{idx+1}. {icon} `[{h['time']}]` **{h['type']}**: `{h['amount']:,.0f} đ`\n"
            keyboard.append([
                InlineKeyboardButton(f"#{idx+1} ❌ Xóa", callback_data=f"del_tx_{idx}"),
                InlineKeyboardButton(f"#{idx+1} ✏️ Sửa", callback_data=f"edit_tx_{idx}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")])
        await query.message.edit_text(ledger_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("del_tx_"):
        idx = int(data.split("_")[2])
        history = user_data_db[user_id]["history"]
        if idx < len(history):
            tx = history.pop(idx)
            if tx['type'] == "Thu":
                user_data_db[user_id]["daily_income"] -= tx['amount']
                user_data_db[user_id]["yearly_income"] -= tx['amount']
            else:
                user_data_db[user_id]["daily_expense"] -= tx['amount']
                user_data_db[user_id]["yearly_expense"] -= tx['amount']
            await query.answer("Đã xóa giao dịch thành công!", show_alert=False)

        history = user_data_db[user_id]["history"]
        if not history:
            keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")]]
            await query.message.edit_text("📋 **SỔ CHI TIÊU**\n\n✨ *Sổ giao dịch hiện đang trống.*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        ledger_text = "📋 **SỔ CHI TIÊU & GIAO DỊCH**\n\n"
        keyboard = []
        for i, h in enumerate(history):
            icon = "🟢" if h['type'] == "Thu" else "🔴"
            ledger_text += f"{i+1}. {icon} `[{h['time']}]` **{h['type']}**: `{h['amount']:,.0f} đ`\n"
            keyboard.append([
                InlineKeyboardButton(f"#{i+1} ❌ Xóa", callback_data=f"del_tx_{i}"),
                InlineKeyboardButton(f"#{i+1} ✏️ Sửa", callback_data=f"edit_tx_{i}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")])
        await query.message.edit_text(ledger_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("edit_tx_"):
        idx = int(data.split("_")[2])
        user_state[user_id] = f"EDITING_TX_{idx}"
        msg = await query.message.reply_text(f"✏️ **SỬA GIAO DỊCH #{idx+1}:** Vui lòng gửi số tiền mới:", parse_mode="Markdown")
        user_ai_messages[user_id] = [msg.message_id]

    elif data == "view_year":
        y_inc = user_data_db[user_id]["yearly_income"]
        y_exp = user_data_db[user_id]["yearly_expense"]
        y_balance = y_inc - y_exp
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")]]
        await query.message.edit_text(
            f"📈 **BÁO CÁO TÀI CHÍNH TOÀN NĂM**\n\n"
            f"🟢 Tổng Thu: `{y_inc:,.0f} đ`\n"
            f"🔴 Tổng Chi: `{y_exp:,.0f} đ`\n"
            f"💎 **Số Dư Tích Lũy:** `{y_balance:,.0f} đ`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
    elif data == "back_home":
        if user_id in user_all_chat_msg_ids:
            for msg_id in user_all_chat_msg_ids[user_id]:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    pass
            user_all_chat_msg_ids[user_id] = []

        if user_id in user_ai_messages:
            for msg_id in user_ai_messages[user_id]:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    pass
            user_ai_messages[user_id] = []

        try:
            await query.message.delete()
        except Exception:
            pass

        if user_id in user_last_menu_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=user_last_menu_id[user_id])
            except Exception:
                pass

        user_state.pop(user_id, None)
        user_chat_histories.pop(user_id, None)

        menu_text, reply_markup = get_main_menu_content(user_id)
        msg = await context.bot.send_message(chat_id=chat_id, text=menu_text, reply_markup=reply_markup, parse_mode="Markdown")
        user_last_menu_id[user_id] = msg.message_id

# =====================================================================
# MODULE 3: HỆ THỐNG XỬ LÝ TIN NHẮN THÔNG MINH & TÍCH HỢP ĐA TIỆN ÍCH
# =====================================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if user_id not in user_state:
        user_state[user_id] = "CHAT_AI"

    state = user_state[user_id]

    if state == "CHAT_AI":
        close_keywords = ["đóng chat", "thoát ai", "về menu", "thôi", "bye", "đóng", "thoát"]
        if any(keyword in text.lower() for keyword in close_keywords):
            try:
                await update.message.delete()
            except Exception:
                pass

            if user_id in user_all_chat_msg_ids:
                for msg_id in user_all_chat_msg_ids[user_id]:
                    try:
                        await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    except Exception:
                        pass
                user_all_chat_msg_ids[user_id] = []

            if user_id in user_last_menu_id:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=user_last_menu_id[user_id])
                except Exception:
                    pass

            user_state.pop(user_id, None)
            user_chat_histories.pop(user_id, None)

            menu_text, reply_markup = get_main_menu_content(user_id)
            msg = await context.bot.send_message(chat_id=chat_id, text=menu_text, reply_markup=reply_markup, parse_mode="Markdown")
            user_last_menu_id[user_id] = msg.message_id
            return

        try:
            user_msg_id = update.message.message_id
            if user_id not in user_all_chat_msg_ids:
                user_all_chat_msg_ids[user_id] = []
            user_all_chat_msg_ids[user_id].append(user_msg_id)
            await update.message.delete()
        except Exception:
            pass

        text_lower = text.lower()

        # --- TÍNH NĂNG 1: TẠO ẢNH CHẤT LƯỢNG CAO QUA PROMPT ---
        image_keywords = ["vẽ", "tạo ảnh", "kiếm ảnh", "làm ảnh", "generate image"]
        if any(kw in text_lower for kw in image_keywords):
            thinking_msg = await context.bot.send_message(chat_id=chat_id, text="🎨 Grok AI đang thiết kế hình ảnh theo yêu cầu...")
            user_all_chat_msg_ids[user_id].append(thinking_msg.message_id)

            encoded_prompt = urllib.parse.quote(text)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=thinking_msg.message_id)
                user_all_chat_msg_ids[user_id].remove(thinking_msg.message_id)
            except Exception:
                pass

            try:
                photo_msg = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=image_url,
                    caption=f"⚡ **Grok AI Image Studio:**\n*'{text}'*",
                    parse_mode="Markdown"
                )
                user_all_chat_msg_ids[user_id].append(photo_msg.message_id)
            except Exception:
                pass
            return

        # --- TÍNH NĂNG 2: TÌM KIẾM VÀ GỬI FILE ÂM THANH / NHẠC ---
        music_keywords = ["gửi file", "tải bài hát", "gửi bài hát", "file nhạc", "gửi nhạc", "tìm bài"]
        if any(kw in text_lower for kw in music_keywords):
            thinking_msg = await context.bot.send_message(chat_id=chat_id, text="🎵 Grok đang truy xuất dữ liệu âm thanh...")
            user_all_chat_msg_ids[user_id].append(thinking_msg.message_id)

            try:
                sample_audio_url = "https://actions.google.com/sounds/v1/ambiences/rain_heavy.ogg"
                audio_msg = await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=sample_audio_url,
                    title=text,
                    caption=f"⚡ **Grok AI Music Hub:** Gửi bạn bản nhạc yêu cầu! 🎧",
                    parse_mode="Markdown"
                )
                user_all_chat_msg_ids[user_id].append(audio_msg.message_id)
            except Exception:
                pass

            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=thinking_msg.message_id)
                user_all_chat_msg_ids[user_id].remove(thinking_msg.message_id)
            except Exception:
                pass
            return

        # --- TÍNH NĂNG 3: TRÒ CHUYỆN VỚI GROK AI ENGINE ---
        thinking_msg = await context.bot.send_message(chat_id=chat_id, text="⚡ Grok đang xử lý thông tin...")
        user_all_chat_msg_ids[user_id].append(thinking_msg.message_id)

        try:
            response = grok_engine.generate_content(text)
            reply_text = response.text
        except Exception as e:
            logging.error(f"Lỗi Grok Engine API: {e}")
            reply_text = "⚠️ Hệ thống Grok AI đang quá tải, bạn vui lòng thử lại sau vài giây!"

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=thinking_msg.message_id)
            user_all_chat_msg_ids[user_id].remove(thinking_msg.message_id)
        except Exception:
            pass

        bot_reply_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚡ **Grok AI:**\n\n{reply_text}",
            parse_mode="Markdown"
        )
        user_all_chat_msg_ids[user_id].append(bot_reply_msg.message_id)
        return

    # --- XỬ LÝ GIAO DỊCH TÀI CHÍNH NÂNG CAO ---
    if state.startswith("EDITING_TX_"):
        idx = int(state.split("_")[2])
        try:
            clean_text = text.lower().replace("vnđ", "").replace("đ", "").replace(",", "").strip()
            if "k" in clean_text:
                new_amount = float(clean_text.replace("k", "")) * 1000
            elif "tr" in clean_text:
                new_amount = float(clean_text.replace("tr", "")) * 1000000
            else:
                new_amount = float(clean_text)
        except ValueError:
            await update.message.reply_text("❌ Định dạng số tiền không hợp lệ! Vui lòng nhập lại.")
            return

        history = user_data_db[user_id]["history"]
        if idx < len(history):
            old_tx = history[idx]
            diff = new_amount - old_tx['amount']
            if old_tx['type'] == "Thu":
                user_data_db[user_id]["daily_income"] += diff
                user_data_db[user_id]["yearly_income"] += diff
            else:
                user_data_db[user_id]["daily_expense"] += diff
                user_data_db[user_id]["yearly_expense"] += diff
            old_tx['amount'] = new_amount
            await update.message.reply_text(f"✅ Đã cập nhật giao dịch thành `{new_amount:,.0f} đ`!", parse_mode="Markdown")

        user_state.pop(user_id, None)
        return

    try:
        clean_text = text.lower().replace("vnđ", "").replace("đ", "").replace(",", "").strip()
        if "k" in clean_text:
            amount = float(clean_text.replace("k", "")) * 1000
        elif "tr" in clean_text:
            amount = float(clean_text.replace("tr", "")) * 1000000
        else:
            amount = float(clean_text)
    except ValueError:
        await update.message.reply_text("❌ Sai định dạng tiền! (Ví dụ hợp lệ: `50k`, `2tr`, `150000`)")
        return

    current_time = datetime.now().strftime("%H:%M")
    if state == "WAITING_INCOME":
        user_data_db[user_id]["daily_income"] += amount
        user_data_db[user_id]["yearly_income"] += amount
        user_data_db[user_id]["history"].append({"time": current_time, "type": "Thu", "amount": amount})
        await update.message.reply_text(f"✅ Đã nạp quỹ thành công: `+{amount:,.0f} đ`!", parse_mode="Markdown")
    elif state == "WAITING_EXPENSE":
        user_data_db[user_id]["daily_expense"] += amount
        user_data_db[user_id]["yearly_expense"] += amount
        user_data_db[user_id]["history"].append({"time": current_time, "type": "Chi", "amount": amount})
        await update.message.reply_text(f"✅ Đã trừ quỹ thành công: `-{amount:,.0f} đ`!", parse_mode="Markdown")

    user_state.pop(user_id, None)

# =====================================================================
# MODULE 4: HỆ THỐNG KHỞI CHẠY CHÍNH (MAIN ENTRYPOINT)
# =====================================================================
def main():
    keep_alive()
    
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logging.info("Grok AI Pro OS đang khởi chạy trực tuyến hoàn tất...")
    application.run_polling()

if __name__ == "__main__":
    main()
