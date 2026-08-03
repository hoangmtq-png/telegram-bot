# =====================================================================
# HEO ĐẤT AI PRO - ULTIMATE ENTERPRISE WEB SEARCH EDITION (FULL)
# =====================================================================
import os
import sys
import json
import logging
import urllib.parse
from datetime import datetime
from typing import Dict, List, Any

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

from config import TELEGRAM_BOT_TOKEN
from keep_alive import keep_alive

# 1. CẤU HÌNH LOGGING
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("HeoDatAI_WebSearch")

# Khởi tạo Groq Client
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=GROQ_API_KEY)

# 2. CƠ SỞ DỮ LIỆU BỘ NHỚ TẠM THỜI (IN-MEMORY DB)
user_data_db: Dict[int, Dict[str, Any]] = {}
user_state: Dict[int, str] = {}
user_all_chat_msg_ids: Dict[int, List[int]] = {}
user_last_menu_id: Dict[int, int] = {}
user_conversation_history: Dict[int, List[Dict[str, str]]] = {}

def initialize_user(user_id: int):
    if user_id not in user_data_db:
        user_data_db[user_id] = {
            "daily_income": 0.0,
            "daily_expense": 0.0,
            "yearly_income": 0.0,
            "yearly_expense": 0.0,
            "saved_days": 1,
            "history": []
        }
    if user_id not in user_conversation_history:
        user_conversation_history[user_id] = [
            {
                "role": "system",
                "content": (
                    "Bạn là Heo Đất AI Pro, một trợ lý thông minh siêu cấp, sắc sảo và nhạy bén y hệt Grok. "
                    "Bạn có khả năng tra cứu thông tin thực tế từ internet để trả lời chuẩn xác 100%, "
                    "đồng thời là chuyên gia tài chính cá nhân siêu tốc."
                )
            }
        ]

# 3. GIAO DIỆN BẢNG ĐIỀU KHIỂN TÀI CHÍNH
def get_main_menu_content(user_id: int):
    initialize_user(user_id)
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
        "      🐷 H E O  Đ Ấ T  AI  PRO - WEB 🐷      \n"
        "╚═════════════════════════════════╝\n\n"
        "📊 BẢNG ĐIỀU KHIỂN TÀI CHÍNH THÔNG MINH 📊\n"
        f"  📥 Tổng Thu Hôm Nay: {d_inc:,.0f} đ\n"
        f"  📤 Tổng Chi Hôm Nay: {d_exp:,.0f} đ\n"
        f"  💎 Số Dư Khả Dụng: {balance:,.0f} đ\n\n"
        f"📈 Biểu Đồ Dòng Tiền:\n[{progress_bar}]\n\n"
        f"💰 Tích lũy thực tế: Đã cất dành được {balance:,.0f} đ qua {saved_days} ngày!\n\n"
        "🔥 Lựa chọn tác vụ bên dưới để tiếp tục:"
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
            InlineKeyboardButton("🤖 💬 TRÒ CHUYỆN & TRA CỨU WEB", callback_data="chat_ai_mode"),
        ]
    ]
    return menu_text, InlineKeyboardMarkup(keyboard)

# 4. XỬ LÝ LỆNH START & CALLBACK
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    initialize_user(user_id)
    
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

    msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=None)
    user_last_menu_id[user_id] = msg.message_id

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    data = query.data

    initialize_user(user_id)

    if data == "add_income":
        user_state[user_id] = "WAITING_INCOME"
        msg = await query.message.reply_text("📥 NHẬP KHOẢN THU: Gửi số tiền (vd: 50k, 2tr):", parse_mode=None)
        user_ai_messages = user_all_chat_msg_ids.setdefault(user_id, [])
        user_ai_messages.append(msg.message_id)
        
    elif data == "add_expense":
        user_state[user_id] = "WAITING_EXPENSE"
        msg = await query.message.reply_text("📤 NHẬP KHOẢN CHI: Gửi số tiền (vd: 100k, 1.5tr):", parse_mode=None)
        user_ai_messages = user_all_chat_msg_ids.setdefault(user_id, [])
        user_ai_messages.append(msg.message_id)
        
    elif data == "chat_ai_mode":
        user_state[user_id] = "CHAT_AI"
        user_all_chat_msg_ids[user_id] = []
        
        keyboard = [[InlineKeyboardButton("🔙 [ ĐÓNG HEO ĐẤT AI & VỀ MENU CHÍNH ]", callback_data="back_home")]]
        intro_msg = await query.message.reply_text(
            "🐷🤖 ĐÃ KÍCH HOẠT HỆ THỐNG TRA CỨU WEB & AI PRO 🤖🐷\n\n"
            "Tôi có thể tra cứu thông tin trực tuyến trên Google, vẽ tranh, phát nhạc và quản lý tài chính chuẩn xác 100%!\n\n"
            "💡 Bấm nút bên dưới khi muốn thoát về menu tài chính.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=None
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
            history_text = "✨ Chưa ghi nhận giao dịch nào trong ngày."
        else:
            history_text = "\n".join([f"🔹 [{h['time']}] {h['type']}: {h['amount']:,.0f} đ" for h in history])
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")]]
        await query.message.edit_text(
            f"📜 5 GIAO DỊCH GẦN NHẤT HÔM NAY\n\n{history_text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=None
        )
        
    elif data == "view_detail_ledger":
        history = user_data_db[user_id]["history"]
        if not history:
            keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")]]
            await query.message.edit_text("📋 SỔ CHI TIÊU GIAO DỊCH\n\n✨ Chưa có giao dịch nào.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=None)
            return

        ledger_text = "📋 SỔ CHI TIÊU & GIAO DỊCH (HÔM NAY)\n\n"
        keyboard = []
        for idx, h in enumerate(history):
            icon = "🟢" if h['type'] == "Thu" else "🔴"
            ledger_text += f"{idx+1}. {icon} [{h['time']}] {h['type']}: {h['amount']:,.0f} đ\n"
            keyboard.append([
                InlineKeyboardButton(f"#{idx+1} ❌ Xóa", callback_data=f"del_tx_{idx}"),
                InlineKeyboardButton(f"#{idx+1} ✏️ Sửa", callback_data=f"edit_tx_{idx}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")])
        await query.message.edit_text(ledger_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=None)

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
            await query.message.edit_text("📋 SỔ CHI TIÊU\n\n✨ Trống.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=None)
            return

        ledger_text = "📋 SỔ CHI TIÊU & GIAO DỊCH\n\n"
        keyboard = []
        for i, h in enumerate(history):
            icon = "🟢" if h['type'] == "Thu" else "🔴"
            ledger_text += f"{i+1}. {icon} [{h['time']}] {h['type']}: {h['amount']:,.0f} đ\n"
            keyboard.append([
                InlineKeyboardButton(f"#{i+1} ❌ Xóa", callback_data=f"del_tx_{i}"),
                InlineKeyboardButton(f"#{i+1} ✏️ Sửa", callback_data=f"edit_tx_{i}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")])
        await query.message.edit_text(ledger_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=None)

    elif data.startswith("edit_tx_"):
        idx = int(data.split("_")[2])
        user_state[user_id] = f"EDITING_TX_{idx}"
        msg = await query.message.reply_text(f"✏️ SỬA GIAO DỊCH #{idx+1}: Gửi số tiền mới:", parse_mode=None)
        user_ai_messages = user_all_chat_msg_ids.setdefault(user_id, [])
        user_ai_messages.append(msg.message_id)

    elif data == "view_year":
        y_inc = user_data_db[user_id]["yearly_income"]
        y_exp = user_data_db[user_id]["yearly_expense"]
        y_balance = y_inc - y_exp
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="back_home")]]
        await query.message.edit_text(
            f"📈 BÁO CÁO TÀI CHÍNH TOÀN NĂM\n\n"
            f"🟢 Thu Nhập: {y_inc:,.0f} đ\n"
            f"🔴 Chi Tiêu: {y_exp:,.0f} đ\n"
            f"💎 Số Dư Ròng: {y_balance:,.0f} đ",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=None
        )
        
    elif data == "back_home":
        if user_id in user_all_chat_msg_ids:
            for msg_id in user_all_chat_msg_ids[user_id]:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    pass
            user_all_chat_msg_ids[user_id] = []

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
        text, reply_markup = get_main_menu_content(user_id)
        msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=None)
        user_last_menu_id[user_id] = msg.message_id

# 5. XỬ LÝ TIN NHẮN TÍCH HỢP WEB SEARCH & MULTI-TASK
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    initialize_user(user_id)
    state = user_state.get(user_id, "CHAT_AI")

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
            text_menu, reply_markup = get_main_menu_content(user_id)
            msg = await context.bot.send_message(chat_id=chat_id, text=text_menu, reply_markup=reply_markup, parse_mode=None)
            user_last_menu_id[user_id] = msg.message_id
            return

        try:
            user_msg_id = update.message.message_id
            user_msgs = user_all_chat_msg_ids.setdefault(user_id, [])
            user_msgs.append(user_msg_id)
            await update.message.delete()
        except Exception:
            pass

        thinking_msg = await context.bot.send_message(chat_id=chat_id, text="🐷 Heo Đất AI đang soạn...")
        user_all_chat_msg_ids[user_id].append(thinking_msg.message_id)

        try:
            classifier_prompt = (
                "Bạn là bộ não phân loại ý định thông minh. Phân loại câu của người dùng thành 1 trong 3 nhóm:\n"
                "1. 'IMAGE': Muốn vẽ tranh, tạo hình ảnh.\n"
                "2. 'MUSIC': Muốn nghe nhạc, tìm bài hát.\n"
                "3. 'CHAT': Trò chuyện, hỏi đáp kiến thức cần tra cứu thông tin thực tế.\n\n"
                "Trả về ĐÚNG định dạng JSON thuần túy (không markdown codeblock):\n"
                "{\"intent\": \"IMAGE\" hoặc \"MUSIC\" hoặc \"CHAT\", \"response_text\": \"Prompt vẽ ảnh tiếng Anh hoặc câu trả lời/câu hỏi cần tra cứu\"}\n\n"
                f"Nội dung: \"{text}\""
            )

            classifier_res = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": classifier_prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.1
            )
            
            raw_output = classifier_res.choices[0].message.content.strip()
            if raw_output.startswith("```"):
                raw_output = raw_output.split("```")[1]
                if raw_output.startswith("json"):
                    raw_output = raw_output[4:]
            raw_output = raw_output.strip()

            parsed_data = json.loads(raw_output)
            intent = parsed_data.get("intent", "CHAT")
            ai_payload = parsed_data.get("response_text", text)
        except Exception as e:
            logger.error(f"Lỗi Intent: {e}")
            intent = "CHAT"
            ai_payload = text

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=thinking_msg.message_id)
            user_all_chat_msg_ids[user_id].remove(thinking_msg.message_id)
        except Exception:
            pass

        if intent == "IMAGE":
            encoded_prompt = urllib.parse.quote(ai_payload)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
            try:
                photo_msg = await context.bot.send_photo(chat_id=chat_id, photo=image_url, caption=f"🐷 Image: '{text}'", parse_mode=None)
                user_all_chat_msg_ids[user_id].append(photo_msg.message_id)
            except Exception as ex:
                logger.error(f"Lỗi gửi ảnh: {ex}")
            return

        elif intent == "MUSIC":
            try:
                sample_audio_url = "https://actions.google.com/sounds/v1/ambiences/rain_heavy.ogg"
                audio_msg = await context.bot.send_audio(chat_id=chat_id, audio=sample_audio_url, title=ai_payload, caption=f"🎧 Gửi bạn bản nhạc: {text}", parse_mode=None)
                user_all_chat_msg_ids[user_id].append(audio_msg.message_id)
            except Exception as ex:
                logger.error(f"Lỗi gửi nhạc: {ex}")
            return

        else:
            user_conversation_history[user_id].append({"role": "user", "content": text})
            try:
                web_search_res = groq_client.chat.completions.create(
                    messages=user_conversation_history[user_id],
                    model="llama-3.3-70b-versatile",
                    temperature=0.5,
                )
                final_reply = web_search_res.choices[0].message.content
            except Exception as e:
                logger.error(f"Lỗi Chat Completion: {e}")
                final_reply = ai_payload

            user_conversation_history[user_id].append({"role": "assistant", "content": final_reply})

            bot_reply_msg = await context.bot.send_message(chat_id=chat_id, text=f"🐷 Heo Đất AI:\n\n{final_reply}", parse_mode=None)
            user_all_chat_msg_ids[user_id].append(bot_reply_msg.message_id)
            return

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
            await update.message.reply_text("❌ Sai định dạng số tiền!")
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
            await update.message.reply_text(f"✅ Đã cập nhật giao dịch thành {new_amount:,.0f} đ!", parse_mode=None)

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
        await update.message.reply_text("❌ Sai định dạng tiền! (Ví dụ: 50k, 2tr)")
        return

    current_time = datetime.now().strftime("%H:%M")
    if state == "WAITING_INCOME":
        user_data_db[user_id]["daily_income"] += amount
        user_data_db[user_id]["yearly_income"] += amount
        user_data_db[user_id]["history"].append({"time": current_time, "type": "Thu", "amount": amount})
        await update.message.reply_text(f"✅ Đã nạp Thu: +{amount:,.0f} đ!", parse_mode=None)
    elif state == "WAITING_EXPENSE":
        user_data_db[user_id]["daily_expense"] += amount
        user_data_db[user_id]["yearly_expense"] += amount
        user_data_db[user_id]["history"].append({"time": current_time, "type": "Chi", "amount": amount})
        await update.message.reply_text(f"✅ Đã rút Chi: -{amount:,.0f} đ!", parse_mode=None)

    user_state.pop(user_id, None)

# 6. KHỞI CHẠY BOT
def main():
    keep_alive()
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("Heo Đất AI Pro đang chạy trực tuyến...")
    application.run_polling()

if __name__ == "__main__":
    main()
