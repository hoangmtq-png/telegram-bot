# ====================================================================================================
# HEO ĐẤT AI PRO - ENTERPRISE CORE 3.6 (FIXED GEMINI MODEL 1.5)
# ====================================================================================================

import os
import sys
import logging
from datetime import time, datetime
from zoneinfo import ZoneInfo
from threading import Thread
from typing import Dict, List, Any, Tuple

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from google import genai
from google.genai import types
from duckduckgo_search import DDGS

# ----------------------------------------------------------------------------------------------------
# 1. CẤU HÌNH WEB SERVER FLASK (KEEP_ALIVE CHO RENDER)
# ----------------------------------------------------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "🐷 Heo Đất AI Pro Bot đang chạy ổn định 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()


# ----------------------------------------------------------------------------------------------------
# 2. CẤU HÌNH MÔI TRƯỜNG & LOGGING
# ----------------------------------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

logging.basicConfig(
    format="%(asctime)s | LEVEL:%(levelname)s | MSG:%(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("EnterpriseProductionCore")

try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
except Exception as e:
    logger.error(f"Khởi tạo Gemini Client thất bại: {e}")
    gemini_client = None

# CẬP NHẬT TÊN MODEL CHUẨN TỪ GOOGLE
GEMINI_MODELS = ["gemini-1.5-flash", "gemini-1.5-pro"]


# ----------------------------------------------------------------------------------------------------
# 3. TRA CỨU WEB
# ----------------------------------------------------------------------------------------------------
def enterprise_search_web(query: str, max_results: int = 3) -> str:
    try:
        logger.info(f"Đang thực hiện tra cứu web cho từ khóa: {query}")
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
            if not results:
                return "Không tìm thấy kết quả trực tuyến phù hợp."
            
            formatted_snippets = []
            for idx, res in enumerate(results, 1):
                title = res.get('title', 'No Title')
                body = res.get('body', 'No Content')
                formatted_snippets.append(f"[{idx}] {title}\n- Nội dung: {body}")
            return "\n\n".join(formatted_snippets)
    except Exception as e:
        logger.error(f"Lỗi khi tra cứu Web Search: {e}")
        return "Không thể kết nối đến internet để tra cứu lúc này."


# ----------------------------------------------------------------------------------------------------
# 4. QUẢN LÝ DỮ LIỆU & BỘ NHỚ THEO DÕI TIN NHẮN
# ----------------------------------------------------------------------------------------------------
enterprise_user_registry: Dict[int, Dict[str, Any]] = {}
enterprise_user_states: Dict[int, str] = {}
enterprise_chat_message_ids: Dict[int, List[int]] = {}


def enterprise_bootstrap_user(user_id: int) -> None:
    if user_id not in enterprise_user_registry:
        enterprise_user_registry[user_id] = {
            "profile_id": user_id,
            "created_at": datetime.now().isoformat(),
            "daily_income": 0.0,
            "daily_expense": 0.0,
            "yearly_income": 0.0,
            "yearly_expense": 0.0,
            "saved_days": 1,
            "transaction_history": [],
            "budget_limit": 15000000.0,
            "target_amount": 50000000.0,
        }
    if user_id not in enterprise_chat_message_ids:
        enterprise_chat_message_ids[user_id] = []


# ----------------------------------------------------------------------------------------------------
# 5. GIAO DIỆN BẢNG ĐIỀU KHIỂN & MỤC TIÊU TÀI CHÍNH
# ----------------------------------------------------------------------------------------------------
def enterprise_calculate_financial_health(user_id: int) -> Dict[str, Any]:
    enterprise_bootstrap_user(user_id)
    data = enterprise_user_registry[user_id]
    inc, exp = data["daily_income"], data["daily_expense"]
    net = inc - exp
    budget = data["budget_limit"]
    burn_rate = (exp / budget * 100) if budget > 0 else 0.0
    
    status = "STABLE"
    if exp > budget:
        status = "CRITICAL_OVER_BUDGET"
    elif burn_rate > 80:
        status = "WARNING_HIGH_BURN"

    return {"income": inc, "expense": exp, "net_balance": net, "burn_rate": burn_rate, "status": status}


def enterprise_render_dashboard_menu(user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    enterprise_bootstrap_user(user_id)
    metrics = enterprise_calculate_financial_health(user_id)
    d_inc, d_exp, balance = metrics["income"], metrics["expense"], metrics["net_balance"]
    
    user_data = enterprise_user_registry[user_id]
    saved_days = user_data["saved_days"]
    budget_limit = user_data["budget_limit"]
    target_amount = user_data.get("target_amount", 50000000.0)
    
    total_saved = max(0.0, user_data["yearly_income"] - user_data["yearly_expense"])
    goal_percentage = min(100.0, (total_saved / target_amount * 100)) if target_amount > 0 else 0.0
    goal_bar_blocks = int(goal_percentage // 10)
    goal_progress_bar = "🟦" * goal_bar_blocks + "⬜️" * (10 - goal_bar_blocks)

    health = metrics["status"]
    badge = "🟢 AN TOÀN"
    if health == "CRITICAL_OVER_BUDGET":
        badge = "🔴 VƯỢT NGÂN SÁCH"
    elif health == "WARNING_HIGH_BURN":
        badge = "🟡 CẢNH BÁO CHI TIÊU"

    dashboard_text = (
        "╔══════════════════════════════════════════════════╗\n"
        "      🐷 HEO ĐẤT AI PRO - ENTERPRISE CORE           \n"
        "╚══════════════════════════════════════════════════╝\n\n"
        f"  📌 Trạng thái: {badge}\n"
        f"  📥 Thu Hôm Nay: {d_inc:,.0f} đ\n"
        f"  📤 Chi Hôm Nay: {d_exp:,.0f} đ\n"
        f"  💎 Dư Trong Ngày: {balance:,.0f} đ\n"
        f"  🛡️ Hạn Mức Chi Tiêu: {budget_limit:,.0f} đ\n"
        "--------------------------------------------------\n"
        f"🎯 **MỤC TIÊU TIẾT KIỆM:** {target_amount:,.0f} đ\n"
        f"💰 **Đã Tích Lũy Được:** {total_saved:,.0f} đ ({goal_percentage:.1f}%)\n"
        f"[{goal_progress_bar}]\n\n"
        f"🗓️ Tích lũy qua {saved_days} ngày hoạt động."
    )

    keyboard = [
        [InlineKeyboardButton("➕ 📥 NẠP THU", callback_data="ent_add_income"), InlineKeyboardButton("➖ 📤 RÚT CHI", callback_data="ent_add_expense")],
        [InlineKeyboardButton("📜 SỔ GIAO DỊCH / SỬA", callback_data="ent_view_history"), InlineKeyboardButton("🎯 ĐỔI MỤC TIÊU", callback_data="ent_set_target")],
        [InlineKeyboardButton("📈 BÁO CÁO NĂM", callback_data="ent_view_year"), InlineKeyboardButton("🤖 💬 TRÒ CHUYỆN AI", callback_data="ent_chat_ai_mode")]
    ]
    return dashboard_text, InlineKeyboardMarkup(keyboard)


async def cleanup_chat_messages(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    if user_id in enterprise_chat_message_ids:
        for msg_id in enterprise_chat_message_ids[user_id]:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception:
                pass
        enterprise_chat_message_ids[user_id] = []


# --- BÁO CÁO TỰ ĐỘNG LÚC 00:00 ĐÊM ---
async def daily_report_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("⏰ Bắt đầu tiến trình gửi Báo cáo Tự động lúc 00:00...")
    for user_id, data in list(enterprise_user_registry.items()):
        try:
            inc = data["daily_income"]
            exp = data["daily_expense"]
            net = inc - exp
            target = data.get("target_amount", 50000000.0)
            total_saved = max(0.0, data["yearly_income"] - data["yearly_expense"])
            goal_pct = min(100.0, (total_saved / target * 100)) if target > 0 else 0.0

            report_msg = (
                "🌙 **BÁO CÁO TỔNG KẾT NGHỈ ĐÊM (00:00)** 🌙\n"
                "═══════════════════════════════════\n"
                f"📥 Thu hôm nay: **{inc:,.0f} đ**\n"
                f"📤 Chi hôm nay: **{exp:,.0f} đ**\n"
                f"⚖️ Dư hôm nay: **{net:,.0f} đ**\n"
                "-----------------------------------\n"
                f"🎯 Mục tiêu: **{target:,.0f} đ**\n"
                f"🏆 Hoàn thành: **{goal_pct:.1f}%** ({total_saved:,.0f} đ)\n"
                "═══════════════════════════════════\n"
                "✨ Hệ thống đã dọn dẹp số liệu ngày cũ để bắt đầu ngày mới!"
            )
            await context.bot.send_message(chat_id=user_id, text=report_msg, parse_mode="Markdown")
            
            data["daily_income"] = 0.0
            data["daily_expense"] = 0.0
            data["saved_days"] += 1
            data["transaction_history"] = []
            
        except Exception as e:
            logger.error(f"Lỗi gửi báo cáo cho User {user_id}: {e}")


# ----------------------------------------------------------------------------------------------------
# 6. XỬ LÝ SỰ KIỆN CALLBACK MENU
# ----------------------------------------------------------------------------------------------------
async def enterprise_command_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    enterprise_bootstrap_user(user_id)
    
    await cleanup_chat_messages(user_id, chat_id, context)
    text, markup = enterprise_render_dashboard_menu(user_id)
    msg = await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    enterprise_chat_message_ids[user_id].append(msg.message_id)


async def enterprise_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    data = query.data

    enterprise_bootstrap_user(user_id)

    if data == "ent_add_income":
        enterprise_user_states[user_id] = "WAITING_INCOME_INPUT"
        kb = [[InlineKeyboardButton("🔙 Hủy bỏ", callback_data="ent_back_home")]]
        await query.message.edit_text("📥 Nhập số tiền thu nhập (Ví dụ: 50k, 2tr, 1.5m):", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "ent_add_expense":
        enterprise_user_states[user_id] = "WAITING_EXPENSE_INPUT"
        kb = [[InlineKeyboardButton("🔙 Hủy bỏ", callback_data="ent_back_home")]]
        await query.message.edit_text("📤 Nhập số tiền chi tiêu (Ví dụ: 100k, 1.5tr):", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "ent_set_target":
        enterprise_user_states[user_id] = "WAITING_TARGET_INPUT"
        kb = [[InlineKeyboardButton("🔙 Hủy bỏ", callback_data="ent_back_home")]]
        curr_target = enterprise_user_registry[user_id].get("target_amount", 50000000.0)
        await query.message.edit_text(
            f"🎯 **Mục tiêu hiện tại:** {curr_target:,.0f} đ\n\n"
            "Hãy nhập Số tiền mục tiêu mới muốn tiết kiệm (Ví dụ: 20tr, 100m, 1 tỷ):",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown"
        )

    elif data == "ent_chat_ai_mode":
        enterprise_user_states[user_id] = "ENTERPRISE_AI_CHAT"
        enterprise_chat_message_ids[user_id] = []
        
        try:
            await query.message.delete()
        except Exception:
            pass
        
        kb = [[InlineKeyboardButton("🔙 [ THOÁT AI & VỀ MENU ]", callback_data="ent_back_home")]]
        init_msg = await context.bot.send_message(
            chat_id=chat_id, 
            text="🐷🤖 Đã kích hoạt chế độ Heo Đất AI Pro.\nHãy gửi nội dung bạn muốn trò chuyện hoặc tra cứu!", 
            reply_markup=InlineKeyboardMarkup(kb)
        )
        enterprise_chat_message_ids[user_id].append(init_msg.message_id)

    elif data == "ent_view_history":
        hist = enterprise_user_registry[user_id]["transaction_history"][-5:]
        content = "\n".join([f"🔹 [{x['time']}] {x['type']}: {x['amount']:,.0f} đ" for x in hist]) if hist else "✨ Chưa có giao dịch nào."
        
        kb = []
        if hist:
            kb.append([InlineKeyboardButton("🔄 XÓA GIAO DỊCH GẦN NHẤT", callback_data="ent_undo_last_tx")])
        kb.append([InlineKeyboardButton("🔙 Quay lại Menu", callback_data="ent_back_home")])
        
        await query.message.edit_text(f"📜 5 Giao dịch gần nhất:\n\n{content}", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "ent_undo_last_tx":
        hist = enterprise_user_registry[user_id]["transaction_history"]
        if hist:
            last_tx = hist.pop()
            val = last_tx["amount"]
            if last_tx["type"] == "Thu":
                enterprise_user_registry[user_id]["daily_income"] = max(0.0, enterprise_user_registry[user_id]["daily_income"] - val)
                enterprise_user_registry[user_id]["yearly_income"] = max(0.0, enterprise_user_registry[user_id]["yearly_income"] - val)
            else:
                enterprise_user_registry[user_id]["daily_expense"] = max(0.0, enterprise_user_registry[user_id]["daily_expense"] - val)
                enterprise_user_registry[user_id]["yearly_expense"] = max(0.0, enterprise_user_registry[user_id]["yearly_expense"] - val)

            await query.answer("✅ Đã xóa giao dịch nhập sai thành công!", show_alert=True)
        else:
            await query.answer("❌ Không có giao dịch nào để xóa!", show_alert=True)
        
        text, markup = enterprise_render_dashboard_menu(user_id)
        await query.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")

    elif data == "ent_view_year":
        reg = enterprise_user_registry[user_id]
        inc, exp = reg["yearly_income"], reg["yearly_expense"]
        kb = [[InlineKeyboardButton("🔙 Quay lại", callback_data="ent_back_home")]]
        await query.message.edit_text(f"📈 Báo cáo tổng quan năm:\n\n🟢 Tổng Thu: {inc:,.0f} đ\n🔴 Tổng Chi: {exp:,.0f} đ", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "ent_back_home":
        await cleanup_chat_messages(user_id, chat_id, context)
        enterprise_user_states.pop(user_id, None)
        
        text, markup = enterprise_render_dashboard_menu(user_id)
        try:
            await query.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode="Markdown")
            enterprise_chat_message_ids[user_id].append(msg.message_id)


# ----------------------------------------------------------------------------------------------------
# 7. XỬ LÝ TIN NHẮN (SỬA LẠI TÊN MODEL GEMINI CHUẨN GOOGLE)
# ----------------------------------------------------------------------------------------------------
async def enterprise_incoming_message_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    raw_text = update.message.text.strip()
    enterprise_bootstrap_user(user_id)

    state = enterprise_user_states.get(user_id, None)

    # --- CHẾ ĐỘ CHAT AI ---
    if state == "ENTERPRISE_AI_CHAT":
        enterprise_chat_message_ids[user_id].append(update.message.message_id)

        exit_keywords = ["đóng chat", "thoát ai", "về menu", "thôi", "bye", "đóng", "thoát", "menu"]
        if any(cmd in raw_text.lower() for cmd in exit_keywords):
            await cleanup_chat_messages(user_id, chat_id, context)
            enterprise_user_states.pop(user_id, None)
            text, markup = enterprise_render_dashboard_menu(user_id)
            msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode="Markdown")
            enterprise_chat_message_ids[user_id].append(msg.message_id)
            return

        thinking = await update.message.reply_text("🐷 Heo Đất AI Pro đang xử lý...")
        enterprise_chat_message_ids[user_id].append(thinking.message_id)

        need_search = False
        search_query = raw_text
        
        if gemini_client:
            try:
                intent_res = gemini_client.models.generate_content(
                    model="gemini-1.5-flash",  # <--- Đã sửa chuẩn Gemini 1.5
                    contents=raw_text,
                    config=types.GenerateContentConfig(
                        system_instruction="Nếu tin nhắn yêu cầu tra cứu thông tin thực tế, tin tức, nghệ sĩ, bài hát, giá cả, hãy trả về 'SEARCH: <từ khóa>'. Ngược lại trả về 'CHAT'.",
                        temperature=0.1
                    )
                )
                if intent_res.text.strip().startswith("SEARCH:"):
                    need_search = True
                    search_query = intent_res.text.strip().replace("SEARCH:", "").strip()
            except Exception as e:
                logger.error(f"Lỗi phân loại ý định: {e}")

        search_data = enterprise_search_web(search_query) if need_search else ""
        
        if need_search and search_data and "Không tìm thấy kết quả" not in search_data:
            prompt_with_context = (
                f"Câu hỏi của người dùng: '{raw_text}'\n"
                f"Dữ liệu thực tế từ Internet:\n{search_data}\n\n"
                f"Yêu cầu: Hãy tổng hợp dữ liệu trên để trả lời chính xác. Tuyệt đối KHÔNG tự sáng tác thêm thông tin sai sự thật."
            )
        else:
            prompt_with_context = raw_text

        system_instruction = (
            "Bạn là trợ lý Heo Đất AI Pro thông minh và trung thực. "
            "QUY TẮC BẮT BUỘC:\n"
            "1. Chỉ trả lời dựa trên sự thật thực tế. Nếu không chắc chắn hoặc không có dữ liệu, hãy thành thật trả lời là không biết.\n"
            "2. Tuyệt đối KHÔNG tự bịa ra tên bài hát, tác giả, tác phẩm hay sự kiện không có thật.\n"
            "3. Xưng hô lịch sự, thân thiện (dùng 'tôi' hoặc 'Heo Đất')."
        )

        reply_content = "⚠️ Chưa cấu hình GEMINI_API_KEY hoặc Key bị lỗi!"
        if gemini_client:
            for model_name in GEMINI_MODELS:
                try:
                    res = gemini_client.models.generate_content(
                        model=model_name,
                        contents=prompt_with_context,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.2
                        )
                    )
                    reply_content = res.text
                    break
                except Exception as e:
                    logger.error(f"Gemini API Error ({model_name}): {e}")

        try:
            await thinking.delete()
            enterprise_chat_message_ids[user_id].remove(thinking.message_id)
        except Exception:
            pass

        ai_msg = await update.message.reply_text(f"🐷 Heo Đất AI Pro:\n\n{reply_content}")
        enterprise_chat_message_ids[user_id].append(ai_msg.message_id)
        return

    # --- CHẾ ĐỘ NHẬP SỐ TIỀN THU / CHI / MỤC TIÊU ---
    if state in ["WAITING_INCOME_INPUT", "WAITING_EXPENSE_INPUT", "WAITING_TARGET_INPUT"]:
        try:
            val = enterprise_parse_amount(raw_text)
        except ValueError:
            await update.message.reply_text("❌ Định dạng số tiền chưa đúng! Ví dụ nhập: 50k, 2tr, 1.5m, 1 tỷ")
            return

        time_str = datetime.now().strftime("%H:%M")
        if state == "WAITING_INCOME_INPUT":
            enterprise_user_registry[user_id]["daily_income"] += val
            enterprise_user_registry[user_id]["yearly_income"] += val
            enterprise_user_registry[user_id]["transaction_history"].append({"time": time_str, "type": "Thu", "amount": val})
            await update.message.reply_text(f"✅ Đã ghi nhận THU: +{val:,.0f} đ")
        elif state == "WAITING_EXPENSE_INPUT":
            enterprise_user_registry[user_id]["daily_expense"] += val
            enterprise_user_registry[user_id]["yearly_expense"] += val
            enterprise_user_registry[user_id]["transaction_history"].append({"time": time_str, "type": "Chi", "amount": val})
            await update.message.reply_text(f"✅ Đã ghi nhận CHI: -{val:,.0f} đ")
        elif state == "WAITING_TARGET_INPUT":
            enterprise_user_registry[user_id]["target_amount"] = val
            await update.message.reply_text(f"🎯 Đã cập nhật MỤC TIÊU MỚI: {val:,.0f} đ")

        enterprise_user_states.pop(user_id, None)
        text, markup = enterprise_render_dashboard_menu(user_id)
        msg = await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
        enterprise_chat_message_ids[user_id].append(msg.message_id)
        return

    # --- NHẮN LINH TINH TỰ XÓA TIN NHẮN RÁC & LÀM MỚI MENU ---
    try:
        await update.message.delete()
    except Exception:
        pass

    await cleanup_chat_messages(user_id, chat_id, context)

    text, markup = enterprise_render_dashboard_menu(user_id)
    new_menu = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup, parse_mode="Markdown")
    enterprise_chat_message_ids[user_id].append(new_menu.message_id)


def enterprise_parse_amount(text: str) -> float:
    cleaned = text.lower().replace("vnđ", "").replace("đ", "").replace(",", "").replace(" ", "").strip()
    mult = 1.0
    if "k" in cleaned:
        mult, cleaned = 1000.0, cleaned.replace("k", "")
    elif "tr" in cleaned or "m" in cleaned:
        mult, cleaned = 1000000.0, cleaned.replace("tr", "").replace("m", "")
    elif "tỷ" in cleaned or "b" in cleaned:
        mult, cleaned = 1000000000.0, cleaned.replace("tỷ", "").replace("b", "")
    return float(cleaned) * mult


# ----------------------------------------------------------------------------------------------------
# 8. KHỞI CHẠY CHÍNH
# ----------------------------------------------------------------------------------------------------
def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("LỖI: Vui lòng cài đặt TELEGRAM_BOT_TOKEN trong Environment Variables của Render!")
        return

    keep_alive()
    logger.info("🌐 Web Server Flask Keep-Alive đã chạy!")

    logger.info("🚀 Đang khởi chạy Telegram Bot...")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    if application.job_queue:
        vietnam_tz = ZoneInfo("Asia/Ho_Chi_Minh")
        target_time = time(hour=0, minute=0, second=0, tzinfo=vietnam_tz)
        application.job_queue.run_daily(daily_report_job, time=target_time)
        logger.info("⏰ Đã thiết lập lịch gửi Báo cáo tự động vào lúc 00:00 mỗi ngày!")

    application.add_handler(CommandHandler("start", enterprise_command_start_handler))
    application.add_handler(CallbackQueryHandler(enterprise_callback_router))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), enterprise_incoming_message_dispatcher))

    application.run_polling()


if __name__ == "__main__":
    main()
