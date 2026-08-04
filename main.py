# ====================================================================================================
# HEO ĐẤT AI PRO - ULTRA MONOLITHIC ENTERPRISE MEGA CORE (FIXED & ENHANCED)
# ====================================================================================================

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

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
from duckduckgo_search import DDGS

# ----------------------------------------------------------------------------------------------------
# CẤU HÌNH MÔI TRƯỜNG & KHỞI TẠO HẠ TẦNG LOGGING
# ----------------------------------------------------------------------------------------------------
try:
    from config import TELEGRAM_BOT_TOKEN
except ImportError:
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

try:
    from keep_alive import keep_alive
except ImportError:
    def keep_alive():
        pass

logging.basicConfig(
    format="%(asctime)s | LEVEL:%(levelname)s | MSG:%(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("enterprise_core_production.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("EnterpriseProductionCore")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    logger.warning("CẢNH BÁO: Không tìm thấy GROQ_API_KEY trong biến môi trường!")

try:
    groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    logger.error(f"Khởi tạo Groq Client thất bại: {e}")
    groq_client = None

GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]


# ----------------------------------------------------------------------------------------------------
# HỆ THỐNG TÌM KIẾM INTERNET THÔNG MINH (OPTIMIZED SEARCH AGENT)
# ----------------------------------------------------------------------------------------------------
def enterprise_search_web(query: str, max_results: int = 3) -> str:
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
            if not results:
                return "Không tìm thấy kết quả trực tuyến phù hợp."
            
            formatted_snippets = []
            for idx, res in enumerate(results, 1):
                title = res.get('title', 'No Title')
                body = res.get('body', 'No Content')
                href = res.get('href', '#')
                formatted_snippets.append(f"[{idx}] {title}\n- Nội dung: {body}\n- Nguồn: {href}")
            
            return "\n\n".join(formatted_snippets)
    except Exception as e:
        logger.error(f"Lỗi khi tra cứu Web Search: {e}")
        return "Không thể kết nối đến internet để tra cứu lúc này."


# ----------------------------------------------------------------------------------------------------
# BỘ NHỚ TRONG & CƠ SỞ DỮ LIỆU ĐĂNG KÝ
# ----------------------------------------------------------------------------------------------------
enterprise_user_registry: Dict[int, Dict[str, Any]] = {}
enterprise_user_states: Dict[int, str] = {}
enterprise_chat_histories: Dict[int, List[Dict[str, str]]] = {}


def enterprise_bootstrap_user(user_id: int) -> None:
    if user_id not in enterprise_user_registry:
        enterprise_user_registry[user_id] = {
            "daily_income": 0.0,
            "daily_expense": 0.0,
            "yearly_income": 0.0,
            "yearly_expense": 0.0,
            "saved_days": 1,
            "transaction_history": [],
            "budget_limit": 15000000.0,
        }

    if user_id not in enterprise_chat_histories:
        enterprise_chat_histories[user_id] = [
            {
                "role": "system",
                "content": (
                    "Bạn là Heo Đất AI Pro, trợ lý thông minh cao cấp kết hợp quản lý tài chính doanh nghiệp. "
                    "Hãy trò chuyện tự nhiên, thân thiện và chính xác với người dùng."
                )
            }
        ]


# ----------------------------------------------------------------------------------------------------
# GIAO DIỆN BẢNG ĐIỀU KHIỂN
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
    elif net > 0:
        status = "EXCELLENT_SURPLUS"

    return {"income": inc, "expense": exp, "net_balance": net, "burn_rate": burn_rate, "status": status}


def enterprise_render_dashboard_menu(user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    enterprise_bootstrap_user(user_id)
    metrics = enterprise_calculate_financial_health(user_id)
    d_inc, d_exp, balance = metrics["income"], metrics["expense"], metrics["net_balance"]
    saved_days = enterprise_user_registry[user_id]["saved_days"]
    budget_limit = enterprise_user_registry[user_id]["budget_limit"]
    health = metrics["status"]

    total = d_inc + d_exp
    progress = ("🟢" * int((d_inc / total) * 10) + "🔴" * (10 - int((d_inc / total) * 10))) if total > 0 else "⚪️" * 10
    
    badge = "🟢 AN TOÀN"
    if health == "CRITICAL_OVER_BUDGET":
        badge = "🔴 VƯỢT NGÂN SÁCH"
    elif health == "WARNING_HIGH_BURN":
        badge = "🟡 CẢNH BÁO CHI TIÊU"

    dashboard_text = (
        "╔══════════════════════════════════════════════════╗\n"
        "      🐷 HEO ĐẤT AI PRO - ENTERPRISE CORE 3.1       \n"
        "╚══════════════════════════════════════════════════╝\n\n"
        f"  📌 Trạng thái: {badge}\n"
        f"  📥 Tổng Thu Nhập: {d_inc:,.0f} đ\n"
        f"  📤 Tổng Chi Tiêu: {d_exp:,.0f} đ\n"
        f"  💎 Số Dư Khả Dụng: {balance:,.0f} đ\n"
        f"  🛡️ Hạn Mức Ngân Sách: {budget_limit:,.0f} đ\n\n"
        f"📈 Biểu đồ dòng tiền:\n[{progress}]\n\n"
        f"💰 Tích lũy qua {saved_days} ngày hoạt động."
    )

    keyboard = [
        [InlineKeyboardButton("➕ 📥 NẠP THU", callback_data="ent_add_income"), InlineKeyboardButton("➖ 📤 RÚT CHI", callback_data="ent_add_expense")],
        [InlineKeyboardButton("📜 SỔ GIAO DỊCH & XÓA", callback_data="ent_view_history"), InlineKeyboardButton("🤖 💬 TRÒ CHUYỆN AI", callback_data="ent_chat_ai_mode")],
        [InlineKeyboardButton("📈 BÁO CÁO NĂM", callback_data="ent_view_year")]
    ]
    return dashboard_text, InlineKeyboardMarkup(keyboard)


# ----------------------------------------------------------------------------------------------------
# XỬ LÝ LỆNH & SỰ KIỆN CALLBACK (ĐÃ SỬA LỖI ĐƠ MENU & THÊM TÍNH NĂNG XÓA GIAO DỊCH)
# ----------------------------------------------------------------------------------------------------
async def enterprise_command_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    enterprise_bootstrap_user(user_id)
    enterprise_user_states.pop(user_id, None)
    text, markup = enterprise_render_dashboard_menu(user_id)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(text=text, reply_markup=markup)
    else:
        await update.message.reply_text(text=text, reply_markup=markup)


async def enterprise_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    enterprise_bootstrap_user(user_id)

    if data == "ent_add_income":
        enterprise_user_states[user_id] = "WAITING_INCOME_INPUT"
        kb = [[InlineKeyboardButton("🔙 Hủy bỏ", callback_data="ent_back_home")]]
        await query.message.edit_text("📥 **Nhập số tiền thu nhập** (Ví dụ: 50k, 2tr, 500000):\n\n*(Nhập trực tiếp số tiền vào khung chat)*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "ent_add_expense":
        enterprise_user_states[user_id] = "WAITING_EXPENSE_INPUT"
        kb = [[InlineKeyboardButton("🔙 Hủy bỏ", callback_data="ent_back_home")]]
        await query.message.edit_text("📤 **Nhập số tiền chi tiêu** (Ví dụ: 100k, 1.5tr):\n\n*(Nhập trực tiếp số tiền vào khung chat)*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "ent_chat_ai_mode":
        enterprise_user_states[user_id] = "ENTERPRISE_AI_CHAT"
        kb = [[InlineKeyboardButton("🔙 [ THOÁT AI & VỀ MENU ]", callback_data="ent_back_home")]]
        await query.message.edit_text("🐷🤖 **Đã kích hoạt chế độ Heo Đất AI Pro.**\n\nBạn có thể nhắn tin hỏi đáp hoặc tra cứu thông tin trực tiếp tại đây!", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "ent_view_history":
        hist = enterprise_user_registry[user_id]["transaction_history"][-5:]
        content = "\n".join([f"🔹 [{x['time']}] **{x['type']}**: {x['amount']:,.0f} đ" for x in hist]) if hist else "✨ Chưa có giao dịch nào được ghi nhận."
        
        kb = [
            [InlineKeyboardButton("↩️ XÓA GIAO DỊCH GẦN NHẤT", callback_data="ent_undo_last_tx")],
            [InlineKeyboardButton("🔙 Quay lại Menu", callback_data="ent_back_home")]
        ]
        await query.message.edit_text(f"📜 **5 Giao dịch gần nhất:**\n\n{content}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "ent_undo_last_tx":
        reg = enterprise_user_registry[user_id]
        if reg["transaction_history"]:
            last_tx = reg["transaction_history"].pop()
            amt = last_tx["amount"]
            if last_tx["type"] == "Thu":
                reg["daily_income"] -= amt
                reg["yearly_income"] -= amt
            else:
                reg["daily_expense"] -= amt
                reg["yearly_expense"] -= amt
            
            await query.answer(f"Đã xóa giao dịch {last_tx['type']} {amt:,.0f}đ thành công!", show_alert=True)
        else:
            await query.answer("Không có giao dịch nào để xóa!", show_alert=True)
        
        # Trở lại màn hình lịch sử
        hist = reg["transaction_history"][-5:]
        content = "\n".join([f"🔹 [{x['time']}] **{x['type']}**: {x['amount']:,.0f} đ" for x in hist]) if hist else "✨ Chưa có giao dịch nào."
        kb = [
            [InlineKeyboardButton("↩️ XÓA GIAO DỊCH GẦN NHẤT", callback_data="ent_undo_last_tx")],
            [InlineKeyboardButton("🔙 Quay lại Menu", callback_data="ent_back_home")]
        ]
        await query.message.edit_text(f"📜 **5 Giao dịch gần nhất (Đã cập nhật):**\n\n{content}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "ent_view_year":
        reg = enterprise_user_registry[user_id]
        inc, exp = reg["yearly_income"], reg["yearly_expense"]
        kb = [[InlineKeyboardButton("🔙 Quay lại", callback_data="ent_back_home")]]
        await query.message.edit_text(f"📈 **Báo cáo năm:**\n\n🟢 Tổng Thu: {inc:,.0f} đ\n🔴 Tổng Chi: {exp:,.0f} đ", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "ent_back_home":
        enterprise_user_states.pop(user_id, None)
        text, markup = enterprise_render_dashboard_menu(user_id)
        await query.message.edit_text(text=text, reply_markup=markup)


# ----------------------------------------------------------------------------------------------------
# BỘ ĐIỀU PHỐI TIN NHẮN CHAT & XỬ LÝ NHẬP LIỆU THU/CHI
# ----------------------------------------------------------------------------------------------------
async def enterprise_incoming_message_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    raw_text = update.message.text.strip()
    chat_id = update.effective_chat.id

    enterprise_bootstrap_user(user_id)
    state = enterprise_user_states.get(user_id, "ENTERPRISE_AI_CHAT")

    # Xóa tin nhắn người dùng nhập để gọn khung chat
    try:
        await update.message.delete()
    except Exception:
        pass

    if state == "ENTERPRISE_AI_CHAT":
        thinking = await context.bot.send_message(chat_id=chat_id, text="🐷 Heo Đất AI Pro đang soạn...")

        need_search = False
        search_query = raw_text
        
        if groq_client:
            for model_name in GROQ_MODELS:
                try:
                    intent_res = groq_client.chat.completions.create(
                        messages=[
                            {
                                "role": "system",
                                "content": "Phân tích ý định. Nếu cần tìm kiếm thông tin thực tế, giá cả, thời sự hãy trả về 'SEARCH: <từ khóa>'. Ngược lại trả về 'CHAT'."
                            },
                            {"role": "user", "content": raw_text}
                        ],
                        model=model_name,
                        temperature=0.1
                    )
                    decision = intent_res.choices[0].message.content.strip()
                    if decision.startswith("SEARCH:"):
                        need_search = True
                        search_query = decision.replace("SEARCH:", "").strip()
                    break
                except Exception:
                    continue

        search_data = enterprise_search_web(search_query) if need_search else ""

        prompt_with_context = (
            f"Câu hỏi: '{raw_text}'\nDữ liệu tra cứu:\n{search_data}" if need_search and search_data else raw_text
        )

        reply_content = "⚠️ Lỗi hệ thống AI."
        if groq_client:
            for model_name in GROQ_MODELS:
                try:
                    temp_messages = list(enterprise_chat_histories[user_id])
                    temp_messages.append({"role": "user", "content": prompt_with_context})
                    
                    res = groq_client.chat.completions.create(
                        messages=temp_messages,
                        model=model_name,
                        temperature=0.7
                    )
                    reply_content = res.choices[0].message.content
                    
                    enterprise_chat_histories[user_id].append({"role": "user", "content": raw_text})
                    enterprise_chat_histories[user_id].append({"role": "assistant", "content": reply_content})
                    break
                except Exception as e:
                    if "429" in str(e):
                        continue

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=thinking.message_id)
        except Exception:
            pass

        await context.bot.send_message(chat_id=chat_id, text=f"🐷 **Heo Đất AI Pro:**\n\n{reply_content}", parse_mode="Markdown")
        return

    # Xử lý khi user đang ở trạng thái nhập số tiền Thu / Chi
    try:
        val = enterprise_parse_amount(raw_text)
    except ValueError:
        m_err = await context.bot.send_message(chat_id=chat_id, text="❌ Sai định dạng số tiền! Vui lòng nhập lại (Ví dụ: 50k, 2tr).")
        await asyncio.sleep(3)
        try:
            await m_err.delete()
        except Exception:
            pass
        return

    time_str = datetime.now().strftime("%H:%M")
    if state == "WAITING_INCOME_INPUT":
        enterprise_user_registry[user_id]["daily_income"] += val
        enterprise_user_registry[user_id]["yearly_income"] += val
        enterprise_user_registry[user_id]["transaction_history"].append({"time": time_str, "type": "Thu", "amount": val})
    elif state == "WAITING_EXPENSE_INPUT":
        enterprise_user_registry[user_id]["daily_expense"] += val
        enterprise_user_registry[user_id]["yearly_expense"] += val
        enterprise_user_registry[user_id]["transaction_history"].append({"time": time_str, "type": "Chi", "amount": val})

    enterprise_user_states.pop(user_id, None)

    # Hiển thị lại bảng điều khiển sau khi nhập thành công
    text, markup = enterprise_render_dashboard_menu(user_id)
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)


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
# KHỞI CHẠY ỨNG DỤNG CHÍNH
# ----------------------------------------------------------------------------------------------------
def main() -> None:
    logger.info("Đang khởi động Heo Đất AI Pro - Enterprise Core 3.1...")
    keep_alive()

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", enterprise_command_start_handler))
    application.add_handler(CallbackQueryHandler(enterprise_callback_router))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), enterprise_incoming_message_dispatcher))

    logger.info("🚀 HỆ THỐNG ĐÃ SẴN SÀNG HOẠT ĐỘNG ỔN ĐỊNH!")
    application.run_polling()


if __name__ == "__main__":
    main()
