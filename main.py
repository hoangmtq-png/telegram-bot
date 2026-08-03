# ====================================================================================================
# HEO ĐẤT AI PRO - ULTRA MONOLITHIC ENTERPRISE MEGA CORE (INTENT ROUTING & SMART SEARCH)
# ====================================================================================================

import os
import sys
import json
import time
import logging
import hashlib
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
    format="%(asctime)s | LEVEL:%(levelname)s | THREAD:%(threadName)s | FILE:%(filename)s:%(lineno)d | MSG:%(message)s",
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


# ----------------------------------------------------------------------------------------------------
# HỆ THỐNG TÌM KIẾM INTERNET THÔNG MINH (OPTIMIZED SEARCH AGENT)
# ----------------------------------------------------------------------------------------------------
def enterprise_search_web(query: str, max_results: int = 3) -> str:
    """Hàm tra cứu thông tin tối ưu hóa cho tiếng Việt và dữ liệu giải trí/âm nhạc."""
    try:
        logger.info(f"Đang thực hiện tra cứu web thông minh cho từ khóa: {query}")
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
            
            if not results and "bài hát" not in query.lower():
                fallback_query = f"bài hát {query}"
                results = [r for r in ddgs.text(fallback_query, max_results=max_results)]

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
# BỘ NHỚ TRONG & CƠ SỞ DỮ LIỆU ĐĂNG KÝ (IN-MEMORY ENTERPRISE REGISTRY)
# ----------------------------------------------------------------------------------------------------
enterprise_user_registry: Dict[int, Dict[str, Any]] = {}
enterprise_user_states: Dict[int, str] = {}
enterprise_message_tracker: Dict[int, List[int]] = {}
enterprise_menu_pointers: Dict[int, int] = {}
enterprise_chat_histories: Dict[int, List[Dict[str, str]]] = {}
enterprise_audit_ledgers: Dict[int, List[Dict[str, Any]]] = {}


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
            "currency_unit": "VND",
            "account_tier": "VIP_ENTERPRISE"
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

    if user_id not in enterprise_audit_ledgers:
        enterprise_audit_ledgers[user_id] = []


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
        "      🐷 HEO ĐẤT AI PRO - ENTERPRISE CORE 3.0       \n"
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
        [InlineKeyboardButton("📜 SỔ GIAO DỊCH", callback_data="ent_view_history"), InlineKeyboardButton("📋 SỔ CHI TIẾT", callback_data="ent_view_detail_ledger")],
        [InlineKeyboardButton("📈 BÁO CÁO NĂM", callback_data="ent_view_year"), InlineKeyboardButton("🤖 💬 TRÒ CHUYỆN AI", callback_data="ent_chat_ai_mode")],
        [InlineKeyboardButton("⚙️ CÀI ĐẶT NGÂN SÁCH", callback_data="ent_settings_budget"), InlineKeyboardButton("📜 KIỂM TOÁN", callback_data="ent_audit_report")]
    ]
    return dashboard_text, InlineKeyboardMarkup(keyboard)


# ----------------------------------------------------------------------------------------------------
# XỬ LÝ LỆNH & SỰ KIỆN CALLBACK
# ----------------------------------------------------------------------------------------------------
async def enterprise_command_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    enterprise_bootstrap_user(user_id)
    text, markup = enterprise_render_dashboard_menu(user_id)

    if user_id in enterprise_menu_pointers:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=enterprise_menu_pointers[user_id])
        except Exception:
            pass

    if update.callback_query:
        try:
            await update.callback_query.message.delete()
        except Exception:
            pass
        await update.callback_query.answer()

    msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
    enterprise_menu_pointers[user_id] = msg.message_id


async def enterprise_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    data = query.data

    enterprise_bootstrap_user(user_id)

    if data == "ent_add_income":
        enterprise_user_states[user_id] = "WAITING_INCOME_INPUT"
        m = await query.message.reply_text("📥 Nhập số tiền thu nhập (Ví dụ: 50k, 2tr):")
        enterprise_message_tracker.setdefault(user_id, []).append(m.message_id)

    elif data == "ent_add_expense":
        enterprise_user_states[user_id] = "WAITING_EXPENSE_INPUT"
        m = await query.message.reply_text("📤 Nhập số tiền chi tiêu (Ví dụ: 100k, 1.5tr):")
        enterprise_message_tracker.setdefault(user_id, []).append(m.message_id)

    elif data == "ent_chat_ai_mode":
        enterprise_user_states[user_id] = "ENTERPRISE_AI_CHAT"
        enterprise_message_tracker[user_id] = []
        kb = [[InlineKeyboardButton("🔙 [ THOÁT AI & VỀ MENU ]", callback_data="ent_back_home")]]
        m = await query.message.reply_text("🐷🤖 Đã kích hoạt chế độ Heo Đất AI Pro. Hãy trò chuyện hoặc tra cứu thông tin với tôi!", reply_markup=InlineKeyboardMarkup(kb))
        enterprise_message_tracker[user_id].append(m.message_id)
        try:
            await query.message.delete()
        except Exception:
            pass

    elif data == "ent_view_history":
        hist = enterprise_user_registry[user_id]["transaction_history"][-5:]
        content = "\n".join([f"🔹 [{x['time']}] {x['type']}: {x['amount']:,.0f} đ" for x in hist]) if hist else "✨ Chưa có giao dịch."
        kb = [[InlineKeyboardButton("🔙 Quay lại", callback_data="ent_back_home")]]
        await query.message.edit_text(f"📜 5 Giao dịch gần nhất:\n\n{content}", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "ent_view_year":
        reg = enterprise_user_registry[user_id]
        inc, exp = reg["yearly_income"], reg["yearly_expense"]
        kb = [[InlineKeyboardButton("🔙 Quay lại", callback_data="ent_back_home")]]
        await query.message.edit_text(f"📈 Báo cáo năm:\n🟢 Thu: {inc:,.0f} đ\n🔴 Chi: {exp:,.0f} đ", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "ent_audit_report":
        audits = enterprise_audit_ledgers[user_id][-5:]
        content = "\n".join([f"[{a['timestamp']}] {a['action']}" for a in audits])
        kb = [[InlineKeyboardButton("🔙 Quay lại", callback_data="ent_back_home")]]
        await query.message.edit_text(f"📜 Nhật ký kiểm toán:\n\n{content}", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "ent_back_home":
        if user_id in enterprise_message_tracker:
            for mid in enterprise_message_tracker[user_id]:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                except Exception:
                    pass
            enterprise_message_tracker[user_id] = []
        try:
            await query.message.delete()
        except Exception:
            pass
        if user_id in enterprise_menu_pointers:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=enterprise_menu_pointers[user_id])
            except Exception:
                pass

        enterprise_user_states.pop(user_id, None)
        text, markup = enterprise_render_dashboard_menu(user_id)
        msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
        enterprise_menu_pointers[user_id] = msg.message_id


# ----------------------------------------------------------------------------------------------------
# BỘ ĐIỀU PHỐI TIN NHẮN & ĐỊNH TUYẾN Ý ĐỊNH THÔNG MINH
# ----------------------------------------------------------------------------------------------------
async def enterprise_incoming_message_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    raw_text = update.message.text.strip()
    chat_id = update.effective_chat.id

    enterprise_bootstrap_user(user_id)
    state = enterprise_user_states.get(user_id, "ENTERPRISE_AI_CHAT")

    if state == "ENTERPRISE_AI_CHAT":
        exit_keywords = ["đóng chat", "thoát ai", "về menu", "thôi", "bye", "đóng", "thoát", "menu"]
        if any(cmd in raw_text.lower() for cmd in exit_keywords):
            try:
                await update.message.delete()
            except Exception:
                pass

            if user_id in enterprise_message_tracker:
                for msg_id in enterprise_message_tracker[user_id]:
                    try:
                        await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    except Exception:
                        pass
                enterprise_message_tracker[user_id] = []

            if user_id in enterprise_menu_pointers:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=enterprise_menu_pointers[user_id])
                except Exception:
                    pass

            enterprise_user_states.pop(user_id, None)
            text, markup = enterprise_render_dashboard_menu(user_id)
            msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
            enterprise_menu_pointers[user_id] = msg.message_id
            return

        try:
            enterprise_message_tracker.setdefault(user_id, []).append(update.message.message_id)
            await update.message.delete()
        except Exception:
            pass

        thinking = await context.bot.send_message(chat_id=chat_id, text="🐷 Heo Đất AI Pro đang soạn...")
        enterprise_message_tracker[user_id].append(thinking.message_id)

        # 1. Phân loại ý định: Chỉ tìm kiếm khi thực sự cần thiết (kiến thức, bài hát, tin tức, giá cả...)
        need_search = False
        search_query = raw_text
        
        if groq_client:
            try:
                intent_res = groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Bạn là bộ định tuyến ý định. Hãy phân tích tin nhắn của người dùng. "
                                "Nếu tin nhắn yêu cầu tìm kiếm thông tin thực tế, kiến thức mới, thời sự, giá cả, hoặc tìm tên bài hát/lời bài hát, hãy trả về 'SEARCH: <từ khóa tìm kiếm>'. "
                                "Nếu đó là lời chào hỏi, trò chuyện thông thường, xã giao, hoặc tự luận cá nhân không cần tra cứu mạng, hãy trả về 'CHAT'."
                            )
                        },
                        {"role": "user", "content": raw_text}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.1
                )
                decision = intent_res.choices[0].message.content.strip()
                if decision.startswith("SEARCH:"):
                    need_search = True
                    search_query = decision.replace("SEARCH:", "").strip()
            except Exception:
                pass

        # 2. Thực hiện tìm kiếm web nếu ý định yêu cầu
        search_data = ""
        if need_search:
            search_data = enterprise_search_web(search_query)

        # 3. Tổng hợp prompt gửi LLM
        if need_search and search_data and "Không tìm thấy kết quả" not in search_data:
            prompt_with_context = (
                f"Câu hỏi của người dùng: '{raw_text}'\n"
                f"Dữ liệu tra cứu từ internet:\n{search_data}\n\n"
                f"Yêu cầu: Hãy tổng hợp thông tin trên để trả lời câu hỏi một cách chính xác, tự nhiên."
            )
        else:
            prompt_with_context = raw_text

        reply_content = raw_text
        if groq_client:
            try:
                temp_messages = list(enterprise_chat_histories[user_id])
                temp_messages.append({"role": "user", "content": prompt_with_context})
                
                res = groq_client.chat.completions.create(
                    messages=temp_messages,
                    model="llama-3.3-70b-versatile",
                    temperature=0.7
                )
                reply_content = res.choices[0].message.content
                
                enterprise_chat_histories[user_id].append({"role": "user", "content": raw_text})
                enterprise_chat_histories[user_id].append({"role": "assistant", "content": reply_content})
            except Exception as e:
                logger.error(f"Groq API Error: {e}")
                reply_content = "Hệ thống đang gặp sự cố kết nối AI."

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=thinking.message_id)
            enterprise_message_tracker[user_id].remove(thinking.message_id)
        except Exception:
            pass

        m = await context.bot.send_message(chat_id=chat_id, text=f"🐷 Heo Đất AI Pro:\n\n{reply_content}")
        enterprise_message_tracker[user_id].append(m.message_id)
        return

    # Xử lý các trạng thái nhập thu/chi thông thường
    try:
        val = enterprise_parse_amount(raw_text)
    except ValueError:
        await update.message.reply_text("❌ Sai định dạng số tiền! (Ví dụ: 50k, 2tr)")
        return

    time_str = datetime.now().strftime("%H:%M")
    if state == "WAITING_INCOME_INPUT":
        enterprise_user_registry[user_id]["daily_income"] += val
        enterprise_user_registry[user_id]["yearly_income"] += val
        enterprise_user_registry[user_id]["transaction_history"].append({"time": time_str, "type": "Thu", "amount": val})
        await update.message.reply_text(f"✅ Đã ghi nhận Thu: +{val:,.0f} đ")
    elif state == "WAITING_EXPENSE_INPUT":
        enterprise_user_registry[user_id]["daily_expense"] += val
        enterprise_user_registry[user_id]["yearly_expense"] += val
        enterprise_user_registry[user_id]["transaction_history"].append({"time": time_str, "type": "Chi", "amount": val})
        await update.message.reply_text(f"✅ Đã ghi nhận Chi: -{val:,.0f} đ")

    enterprise_user_states.pop(user_id, None)


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
# KHỞI CHẠY ỨNG DỤNG CHÍNH (ENTRY POINT)
# ----------------------------------------------------------------------------------------------------
def main() -> None:
    logger.info("Đang khởi động Heo Đất AI Pro - Enterprise Core 3.0 (Smart Intent Routing)...")
    keep_alive()

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", enterprise_command_start_handler))
    application.add_handler(CallbackQueryHandler(enterprise_callback_router))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), enterprise_incoming_message_dispatcher))

    logger.info("🚀 HỆ THỐNG ĐÃ SẴN SÀNG VỚI HỆ THỐNG PHÂN LOẠI TÌM KIẾM THÔNG MINH!")
    application.run_polling()


if __name__ == "__main__":
    main()
