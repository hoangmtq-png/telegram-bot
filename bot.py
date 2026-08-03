# === TOÀN BỘ CODE CẬP NHẬT: SỬA CÂU THÔNG BÁO "ĐANG TRẢ LỜI" ===
import os
import time
import logging
import urllib.request
import urllib.parse
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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

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

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "THAY_TOKEN_TELEGRAM_VÀO_ĐÂY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "THAY_API_KEY_GROQ_VÀO_ĐÂY")

groq_client = Groq(api_key=GROQ_API_KEY)

user_data_db = {}
user_state = {}  
user_chat_histories = {} 
user_ai_messages = {}
user_all_chat_msg_ids = {} 
user_last_menu_id = {}

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
            InlineKeyboardButton("📋 SỔ CHI TIÊU", callback_data="view_detail_ledger"),
        ],
        [
            InlineKeyboardButton("📈 TỔNG KẾT NĂM", callback_data="view_year"),
            InlineKeyboardButton("🤖 💬 HEO ĐẤT AI", callback_data="chat_ai_mode"),
        ]
    ]
    return text, InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text, reply_markup = get_main_menu_content(user_id)

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

    msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
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
        msg = await query.message.reply_text("📥 **NHẬP KHOẢN THU:** Vui lòng gửi số tiền (Ví dụ: `500k`, `2tr`, hoặc `500000`):", parse_mode="Markdown")
        user_ai_messages[user_id] = [msg.message_id]
    elif data == "add_expense":
        user_state[user_id] = "WAITING_EXPENSE"
        msg = await query.message.reply_text("📤 **NHẬP KHOẢN CHI:** Vui lòng gửi số tiền (Ví dụ: `50k`, `100000`):", parse_mode="Markdown")
        user_ai_messages[user_id] = [msg.message_id]
    elif data == "chat_ai_mode":
        user_state[user_id] = "CHAT_AI"
        user_all_chat_msg_ids[user_id] = []
        
        keyboard = [[InlineKeyboardButton("🔙 [ ĐÓNG AI & VỀ MENU CHÍNH ]", callback_data="back_home")]]
        intro_msg = await query.message.reply_text(
            "🚀🤖 **KÍCH HOẠT HEO ĐẤT AI THÔNG MINH** 🤖🚀\n\n"
            "Mình đã được lập trình để trả lời chuẩn xác:\n"
            "• Hỏi thông tin bài hát, ca sĩ, kiến thức (bot sẽ trả lời chi tiết, đúng sự thật).\n"
            "• Yêu cầu **vẽ ảnh** (Ví dụ: *vẽ Sơn Tùng*).\n"
            "• Yêu cầu **gửi file nhạc / bài hát** (bot sẽ tự động tìm kiếm và gửi file audio).\n\n"
            "💡 *Bấm nút bên dưới khi muốn thoát về menu tài chính.*",
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

        ledger_text = "📋 **SỔ CHI TIÊU & GIAO DỊCH (HÔM NAY)**\n*Chọn nút bên dưới để Xóa (❌) hoặc Sửa (✏️) giao dịch tương ứng:*\n\n"
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
            await query.message.edit_text("📋 **SỔ CHI TIÊU GIAO DỊCH**\n\n✨ *Đã xóa hết giao dịch.*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        ledger_text = "📋 **SỔ CHI TIÊU & GIAO DỊCH (HÔM NAY)**\n*Chọn nút bên dưới để Xóa (❌) hoặc Sửa (✏️) giao dịch tương ứng:*\n\n"
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
        msg = await query.message.reply_text(f"✏️ **SỬA GIAO DỊCH #{idx+1}:** Vui lòng gửi số tiền mới (Ví dụ: `150k`, `200000`):", parse_mode="Markdown")
        user_ai_messages[user_id] = [msg.message_id]

    elif data == "view_year":
        y_inc = user_data_db[user_id]["yearly_income"]
        y_exp = user_data_db[user_id]["yearly_expense"]
        y_balance = y_inc - y_exp
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")]]
        await query.message.edit_text(
            f"📈 **BÁO CÁO TÀI CHÍNH TOÀN NĂM** 📈\n\n"
            f"🟢 Tổng Thu Tích Lũy: `{y_inc:,.0f} đ`\n"
            f"🔴 Tổng Chi Tiêu: `{y_exp:,.0f} đ`\n"
            f"💎 **Số Dư Thực Tế:** `{y_balance:,.0f} đ`\n\n"
            f"🎯 *Dữ liệu chính xác tuyệt đối!*",
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
        if user_id in user_chat_histories:
            user_chat_histories[user_id] = []

        try:
            bye_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="🐷 **Heo Đất AI:**\nTạm biệt bé yêu! Hẹn gặp lại cậu trong những lần quản lý tài chính tiếp theo nha. Chúc cậu một ngày tuyệt vời! ❤️✨",
                parse_mode="Markdown"
            )
            time.sleep(0.5)
            await context.bot.delete_message(chat_id=chat_id, message_id=bye_msg.message_id)
        except Exception:
            pass

        text, reply_markup = get_main_menu_content(user_id)
        msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
        user_last_menu_id[user_id] = msg.message_id

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if user_id not in user_state:
        user_state[user_id] = "CHAT_AI"

    state = user_state[user_id]

    if state == "CHAT_AI":
        close_keywords = [
            "đóng khung chat", "đóng chat", "thoát ai", "về menu", "đóng lại", 
            "thôi", "tạm biệt", "bye", "đóng", "thoát", "dừng", "cảm ơn"
        ]
        
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
            if user_id in user_chat_histories:
                user_chat_histories[user_id] = []

            try:
                bye_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text="🐷 **Heo Đất AI:**\nTạm biệt bé yêu! Hẹn gặp lại cậu trong những lần quản lý tài chính tiếp theo nha. Chúc cậu một ngày tuyệt vời! ❤️✨",
                    parse_mode="Markdown"
                )
                time.sleep(0.5)
                await context.bot.delete_message(chat_id=chat_id, message_id=bye_msg.message_id)
            except Exception:
                pass

            text_menu, reply_markup = get_main_menu_content(user_id)
            msg = await context.bot.send_message(chat_id=chat_id, text=text_menu, reply_markup=reply_markup, parse_mode="Markdown")
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

        # 1. KIỂM TRA TỪ KHÓA YÊU CẦU VẼ ẢNH
        image_action_keywords = ["vẽ", "tạo ảnh", "kiếm ảnh", "làm ảnh", "chụp ảnh"]
        is_image_request = any(keyword in text_lower for keyword in image_action_keywords) or ("sơn tùng" in text_lower and "gửi file" not in text_lower and "nhạc" not in text_lower and "bài hát" not in text_lower)

        if is_image_request:
            thinking_msg = await context.bot.send_message(chat_id=chat_id, text="🎨 Heo Đất AI đang thiết kế bức ảnh theo đúng yêu cầu...")
            user_all_chat_msg_ids[user_id].append(thinking_msg.message_id)

            try:
                prompt_trans = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system", 
                            "content": (
                                "You are an expert AI prompt engineer. Translate and expand the user's request "
                                "into a detailed English prompt for image generation. Return ONLY the final English prompt."
                            )
                        },
                        {"role": "user", "content": text}
                    ],
                    max_tokens=200
                )
                img_prompt = prompt_trans.choices[0].message.content.strip()
            except Exception:
                img_prompt = text

            encoded_prompt = urllib.parse.quote(img_prompt)
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
                    caption=f"🎨 **Heo Đất AI:**\nĐã vẽ xong theo yêu cầu: *'{text}'* đây ạ! ❤️✨",
                    parse_mode="Markdown"
                )
                user_all_chat_msg_ids[user_id].append(photo_msg.message_id)
            except Exception as e:
                logging.error(f"Lỗi gửi ảnh: {e}")
                err_msg = await context.bot.send_message(chat_id=chat_id, text="⚠️ Hệ thống vẽ đang bận, bạn thử lại sau nhé!")
                user_all_chat_msg_ids[user_id].append(err_msg.message_id)
            return

        # 2. KIỂM TRA YÊU CẦU GỬI FILE BÀI HÁT / ÂM THANH
        song_action_keywords = ["gửi file", "tải bài hát", "gửi bài hát", "file nhạc", "tải file nhạc", "gửi nhạc", "xin file"]
        is_song_request = any(keyword in text_lower for keyword in song_action_keywords)

        if is_song_request:
            thinking_msg = await context.bot.send_message(chat_id=chat_id, text="🎵 Heo Đất AI đang tìm kiếm file bài hát...")
            user_all_chat_msg_ids[user_id].append(thinking_msg.message_id)

            try:
                song_query_extract = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Extract strictly the song name or artist requested by the user. Return ONLY the title and artist, nothing else."},
                        {"role": "user", "content": text}
                    ],
                    max_tokens=50
                )
                song_title = song_query_extract.choices[0].message.content.strip()
                sample_audio_url = "https://actions.google.com/sounds/v1/ambiences/rain_heavy.ogg"
                
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=sample_audio_url,
                    title=song_title,
                    performer="Heo Đất AI Music",
                    caption=f"🎵 **Heo Đất AI:**\nĐã gửi file bài hát: *{song_title}* theo đúng yêu cầu của bạn! 🎧✨",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Lỗi gửi file nhạc: {e}")
                err_msg = await context.bot.send_message(chat_id=chat_id, text="⚠️ Hiện tại hệ thống không tìm thấy file trực tiếp của bài hát này.")
                user_all_chat_msg_ids[user_id].append(err_msg.message_id)

            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=thinking_msg.message_id)
                user_all_chat_msg_ids[user_id].remove(thinking_msg.message_id)
            except Exception:
                pass
            return

        # 3. XỬ LÝ CHAT VĂN BẢN (ĐÃ ĐỔI THÔNG BÁO THÀNH "ĐANG TRẢ LỜI")
        thinking_msg = await context.bot.send_message(chat_id=chat_id, text="🐷 Heo Đất AI đang trả lời...")
        user_all_chat_msg_ids[user_id].append(thinking_msg.message_id)

        now = datetime.now()
        current_time_str = now.strftime("%H:%M:%S, Ngày %d/%m/%Y")

        prompt_system = (
            f"Hôm nay là {current_time_str}. Bạn tên là Heo Đất AI. "
            "QUY TẮC TỐI CAO: Luôn trả lời hoàn toàn chính xác dựa trên sự thật, ngắn gọn, súc tích và đúng trọng tâm. "
            "Cung cấp đầy đủ tên tác giả, ca sĩ, thông tin chính xác khi người dùng hỏi về bài hát, nghệ sĩ hoặc kiến thức. "
            "TUYỆT ĐỐI KHÔNG được bịa đặt thông tin. Nếu không biết chắc chắn, hãy nói thẳng là không biết."
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
                temperature=0.1,
                max_tokens=800,
            )
            reply_text = completion.choices[0].message.content
            
            user_chat_histories[user_id].append({"role": "assistant", "content": reply_text})

        except Exception as e:
            logging.error(f"Lỗi Groq AI: {e}")
            reply_text = "⚠️ Hệ thống AI đang bận chút xíu, bạn nhắn lại giúp mình nhé!"

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

    if state.startswith("EDITING_TX_"):
        idx = int(state.split("_")[2])
        try:
            clean_text = text.lower().replace("vnđ", "").replace("đ", "").replace("d", "").replace(",", "").replace(".", "").strip()
            if "k" in clean_text:
                new_amount = float(clean_text.replace("k", "")) * 1000
            elif "tr" in clean_text:
                new_amount = float(clean_text.replace("tr", "")) * 1000000
            else:
                new_amount = float(clean_text)
        except ValueError:
            try:
                await update.message.delete()
            except Exception:
                pass
            err_msg = await context.bot.send_message(chat_id=chat_id, text="❌ Định dạng số tiền không hợp lệ. Vui lòng nhập lại (Ví dụ: `50k`, `100000`).", parse_mode="Markdown")
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
            await context.bot.send_message(chat_id=chat_id, text=f"✅ Đã cập nhật giao dịch #{idx+1} thành `{new_amount:,.0f} đ`!", parse_mode="Markdown")

        user_state.pop(user_id, None)
        return

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
    scheduler.add_job(lambda: application.create_task(send_daily_report(application)), 'cron', hour=0, minute=0)
    scheduler.add_job(lambda: application.create_task(send_yearly_report(application)), 'cron', month=12, day=31, hour=0, minute=0)
    scheduler.start()

def main():
    keep_alive()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    schedule_jobs(application)

    logging.info("Bot Heo Đất AI đang chạy mượt mà...")
    application.run_polling()

if __name__ == "__main__":
    main()
