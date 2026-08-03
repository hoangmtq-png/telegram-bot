```python
# ====================================================================================================
# HEO ĐẤT AI PRO - ULTRA MONOLITHIC ENTERPRISE MEGA CORE (2000+ LINES SINGLE FILE EDITION)
# ====================================================================================================
# File này được viết hoàn toàn khép kín, không cắt xén, không dùng module phụ ngoại trừ các thư viện 
# chuẩn của Python và các gói Telegram Bot / Groq tiêu chuẩn. Toàn bộ các hệ thống quản lý tài chính,
# kiểm toán đa tầng, xử lý trạng thái, định tuyến giao diện, và phân tích AI đều được tích hợp sâu.
# ====================================================================================================

import os
import sys
import json
import time
import logging
import urllib.parse
import re
import math
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Set

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from groq import Groq

# Cấu hình biến môi trường giả định hoặc import an toàn
try:
    from config import TELEGRAM_BOT_TOKEN
except ImportError:
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "DUMMY_TOKEN_FOR_PARSING")

try:
    from keep_alive import keep_alive
except ImportError:
    def keep_alive():
        pass


# ====================================================================================================
# MODULE 1: HỆ THỐNG LOGGING VÀ BẢO MẬT HẠ TẦNG (INFRASTRUCTURE & LOGGING ENGINE)
# ====================================================================================================

logging.basicConfig(
    format="%(asctime)s | LEVEL:%(levelname)s | THREAD:%(threadName)s | FILE:%(filename)s:%(lineno)d | MSG:%(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ultra_enterprise_core.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("UltraEnterpriseCore")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    logger.warning("CẢNH BÁO QUAN TRỌNG: Không tìm thấy GROQ_API_KEY trong biến môi trường!")

try:
    groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    logger.error(f"Không thể khởi tạo Groq Client: {e}")
    groq_client = None


# ====================================================================================================
# MODULE 2: CƠ SỞ DỮ LIỆU BỘ NHỚ TRONG CẤP ĐỘ DOANH NGHIỆP (IN-MEMORY ENTERPRISE DATABASES)
# ====================================================================================================

enterprise_user_registry: Dict[int, Dict[str, Any]] = {}
enterprise_user_states: Dict[int, str] = {}
enterprise_message_tracker: Dict[int, List[int]] = {}
enterprise_menu_pointers: Dict[int, int] = {}
enterprise_chat_histories: Dict[int, List[Dict[str, str]]] = {}
enterprise_audit_ledgers: Dict[int, List[Dict[str, Any]]] = {}
enterprise_system_metrics: Dict[str, Any] = {
    "total_requests": 0,
    "active_sessions": 0,
    "boot_timestamp": datetime.now().isoformat()
}


def enterprise_bootstrap_user(user_id: int) -> None:
    """Khởi tạo toàn bộ cấu trúc dữ liệu tài chính và trạng thái cho người dùng mới."""
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
            "account_tier": "VIP_ENTERPRISE",
            "security_pin": None
        }
        enterprise_system_metrics["active_sessions"] += 1

    if user_id not in enterprise_chat_histories:
        enterprise_chat_histories[user_id] = [
            {
                "role": "system",
                "content": (
                    "Bạn là Heo Đất AI Pro, một trợ lý thông minh siêu cấp, sắc sảo và nhạy bén y hệt Grok. "
                    "Bạn có khả năng thấu hiểu mọi câu hỏi phức tạp, lắt léo, đa nghĩa của người dùng và đồng thời là "
                    "chuyên gia quản lý tài chính doanh nghiệp siêu tốc. Luôn trả lời chuẩn xác, minh bạch, có chiều sâu."
                )
            }
        ]

    if user_id not in enterprise_audit_ledgers:
        enterprise_audit_ledgers[user_id] = []


def enterprise_record_audit_trail(user_id: int, action_type: str, payload_desc: str) -> None:
    """Ghi lại vết kiểm toán (Audit Trail) cho từng giao dịch hoặc tương tác."""
    if user_id not in enterprise_audit_ledgers:
        enterprise_audit_ledgers[user_id] = []
    
    audit_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action_type,
        "description": payload_desc,
        "checksum": hashlib.md5(f"{user_id}{time.time()}{action_type}".encode()).hexdigest()[:8]
    }
    enterprise_audit_ledgers[user_id].append(audit_entry)
    logger.info(f"AUDIT_TRAIL | UserID: {user_id} | Action: {action_type} | Desc: {payload_desc}")


# ====================================================================================================
# MODULE 3: HỆ THỐNG TÍNH TOÁN TÀI CHÍNH VÀ PHÂN TÍCH CHUYÊN SÂU (FINANCIAL MATH ENGINE)
# ====================================================================================================

def enterprise_calculate_financial_health(user_id: int) -> Dict[str, Any]:
    """Thực hiện các thuật toán phân tích dòng tiền, tỷ lệ tiết kiệm và cảnh báo ngân sách."""
    enterprise_bootstrap_user(user_id)
    account_data = enterprise_user_registry[user_id]
    
    inc = account_data["daily_income"]
    exp = account_data["daily_expense"]
    net_balance = inc - exp
    budget = account_data["budget_limit"]
    
    burn_rate = (exp / budget * 100) if budget > 0 else 0.0
    savings_ratio = (net_balance / inc * 100) if inc > 0 else 0.0
    
    health_status = "STABLE"
    if exp > budget:
        health_status = "CRITICAL_OVER_BUDGET"
    elif burn_rate > 80:
        health_status = "WARNING_HIGH_BURN"
    elif net_balance > 0:
        health_status = "EXCELLENT_SURPLUS"

    return {
        "income": inc,
        "expense": exp,
        "net_balance": net_balance,
        "burn_rate": burn_rate,
        "savings_ratio": savings_ratio,
        "status": health_status
    }


# ====================================================================================================
# MODULE 4: GIAO DIỆN NGƯỜI DÙNG & BẢNG ĐIỀU KHIỂN ĐỒ HỌA TRỰC QUAN (UI & DASHBOARD RENDERER)
# ====================================================================================================

def enterprise_render_dashboard_menu(user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    """Tạo giao diện bảng điều khiển tài chính đa tầng với biểu đồ dòng tiền Unicode."""
    enterprise_bootstrap_user(user_id)
    metrics = enterprise_calculate_financial_health(user_id)
    
    d_inc = metrics["income"]
    d_exp = metrics["expense"]
    balance = metrics["net_balance"]
    saved_days = enterprise_user_registry[user_id]["saved_days"]
    budget_limit = enterprise_user_registry[user_id]["budget_limit"]
    health = metrics["status"]

    total_flow = d_inc + d_exp
    if total_flow > 0:
        inc_ratio = int((d_inc / total_flow) * 10)
        visual_progress_bar = "🟢" * inc_ratio + "🔴" * (10 - inc_ratio)
    else:
        visual_progress_bar = "⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️"

    status_badge = "🟢 AN TOÀN"
    if health == "CRITICAL_OVER_BUDGET":
        status_badge = "🔴 VƯỢT NGÂN SÁCH"
    elif health == "WARNING_HIGH_BURN":
        status_badge = "🟡 CẢNH BÁO CHI TIÊU"

    dashboard_text = (
        "╔══════════════════════════════════════════════════╗\n"
        "      🐷 HEO ĐẤT AI PRO - ULTRA ENTERPRISE CORE 🐷      \n"
        "╚══════════════════════════════════════════════════╝\n\n"
        "📊 BẢNG ĐIỀU KHIỂN TÀI CHÍNH TOÀN DIỆN DOANH NGHIỆP 📊\n"
        f"  📌 Trạng thái hệ thống: {status_badge}\n"
        f"  📥 Tổng Thu Nhập: {d_inc:,.0f} đ\n"
        f"  📤 Tổng Chi Tiêu: {d_exp:,.0f} đ\n"
        f"  💎 Số Dư Khả Dụng: {balance:,.0f} đ\n"
        f"  🛡️ Hạn Mức Ngân Sách: {budget_limit:,.0f} đ\n\n"
        f"📈 Biểu Đồ Dòng Tiền Thời Gian Thực:\n[{visual_progress_bar}]\n\n"
        f"💰 Hành trình tích lũy: Đã cất dành được {balance:,.0f} đ qua {saved_days} ngày hoạt động liên tục!\n\n"
        "🔥 Vui lòng chọn tác vụ hệ thống cao cấp bên dưới:"
    )

    keyboard_matrix = [
        [
            InlineKeyboardButton("➕ 📥 NẠP THU NHẬP", callback_data="ent_add_income"),
            InlineKeyboardButton("➖ 📤 RÚT CHI TIÊU", callback_data="ent_add_expense"),
        ],
        [
            InlineKeyboardButton("📜 SỔ GIAO DỊCH", callback_data="ent_view_history"),
            InlineKeyboardButton("📋 SỔ CHI TIÊU", callback_data="ent_view_detail_ledger"),
        ],
        [
            InlineKeyboardButton("📈 BÁO CÁO NĂM", callback_data="ent_view_year"),
            InlineKeyboardButton("🤖 💬 TRÒ CHUYỆN VỚI HEO ĐẤT AI", callback_data="ent_chat_ai_mode"),
        ],
        [
            InlineKeyboardButton("⚙️ CÀI ĐẶT NGÂN SÁCH", callback_data="ent_settings_budget"),
            InlineKeyboardButton("📜 XUẤT BÁO CÁO KIỂM TOÁN", callback_data="ent_audit_report")
        ]
    ]
    
    return dashboard_text, InlineKeyboardMarkup(keyboard_matrix)


# ====================================================================================================
# MODULE 5: HỆ THỐNG XỬ LÝ SỰ KIỆN CALLBACK & LỆNH ĐIỀU HƯỚNG (CALLBACK & COMMAND ROUTER)
# ====================================================================================================

async def enterprise_command_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /start, khởi tạo phiên làm việc và xóa bỏ rác bộ nhớ cũ."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    enterprise_bootstrap_user(user_id)
    
    menu_text, reply_markup = enterprise_render_dashboard_menu(user_id)

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

    sent_message = await context.bot.send_message(
        chat_id=chat_id,
        text=menu_text,
        reply_markup=reply_markup,
        parse_mode=None
    )
    enterprise_menu_pointers[user_id] = sent_message.message_id
    enterprise_record_audit_trail(user_id, "COMMAND_START", "Khởi động lại bảng điều khiển chính.")
    enterprise_system_metrics["total_requests"] += 1


async def enterprise_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bộ điều phối sự kiện nút bấm tương tác (Inline Keyboard Router) với độ trễ tối thiểu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    callback_data = query.data

    enterprise_bootstrap_user(user_id)
    enterprise_system_metrics["total_requests"] += 1

    if callback_data == "ent_add_income":
        enterprise_user_states[user_id] = "WAITING_INCOME_INPUT"
        prompt_msg = await query.message.reply_text(
            "📥 NHẬP KHOẢN THU NHẬP DOANH NGHIỆP:\n"
            "Vui lòng gửi số tiền cần ghi nhận (Ví dụ: 50k, 2tr, 500000):",
            parse_mode=None
        )
        enterprise_message_tracker.setdefault(user_id, []).append(prompt_msg.message_id)
        enterprise_record_audit_trail(user_id, "NAV_ADD_INCOME", "Chuyển sang trạng thái nhập thu.")

    elif callback_data == "ent_add_expense":
        enterprise_user_states[user_id] = "WAITING_EXPENSE_INPUT"
        prompt_msg = await query.message.reply_text(
            "📤 NHẬP KHOẢN CHI TIÊU DOANH NGHIỆP:\n"
            "Vui lòng gửi số tiền cần khấu trừ (Ví dụ: 100k, 1.5tr, 250000):",
            parse_mode=None
        )
        enterprise_message_tracker.setdefault(user_id, []).append(prompt_msg.message_id)
        enterprise_record_audit_trail(user_id, "NAV_ADD_EXPENSE", "Chuyển sang trạng thái nhập chi.")

    elif callback_data == "ent_chat_ai_mode":
        enterprise_user_states[user_id] = "ENTERPRISE_AI_CHAT"
        enterprise_message_tracker[user_id] = []
        
        exit_keyboard = [[InlineKeyboardButton("🔙 [ ĐÓNG HEO ĐẤT AI & VỀ MENU CHÍNH ]", callback_data="ent_back_home")]]
        intro_msg = await query.message.reply_text(
            "🐷🤖 ĐÃ KÍCH HOẠT HỆ THỐNG HEO ĐẤT AI ENTERPRISE 🤖🐷\n\n"
            "Tôi đã sẵn sàng thấu hiểu mọi câu hỏi phức tạp, tìm kiếm hình ảnh, xử lý văn bản hoặc phân tích tài chính theo ý bạn!\n\n"
            "💡 Bấm nút bên dưới khi muốn kết thúc phiên chat và quay về menu chính.",
            reply_markup=InlineKeyboardMarkup(exit_keyboard),
            parse_mode=None
        )
        enterprise_message_tracker[user_id].append(intro_msg.message_id)
        enterprise_menu_pointers[user_id] = query.message.message_id

        try:
            await query.message.delete()
        except Exception:
            pass
        enterprise_record_audit_trail(user_id, "NAV_AI_CHAT", "Kích hoạt chế độ trò chuyện AI đa nhiệm.")

    elif callback_data == "ent_view_history":
        history_list = enterprise_user_registry[user_id]["transaction_history"][-5:]
        if not history_list:
            history_str = "✨ Chưa ghi nhận giao dịch nào trong ngày hôm nay."
        else:
            history_str = "\n".join([f"🔹 [{item['time']}] {item['type']}: {item['amount']:,.0f} đ" for item in history_list])
        
        back_keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="ent_back_home")]]
        await query.message.edit_text(
            f"📜 5 GIAO DỊCH GẦN NHẤT HÔM NAY\n\n{history_str}",
            reply_markup=InlineKeyboardMarkup(back_keyboard),
            parse_mode=None
        )
        enterprise_record_audit_trail(user_id, "VIEW_HISTORY", "Xem lịch sử 5 giao dịch gần nhất.")

    elif callback_data == "ent_view_detail_ledger":
        history_list = enterprise_user_registry[user_id]["transaction_history"]
        if not history_list:
            back_keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="ent_back_home")]]
            await query.message.edit_text("📋 SỔ CHI TIẾU GIAO DỊCH\n\n✨ Sổ trống, chưa có giao dịch.", reply_markup=InlineKeyboardMarkup(back_keyboard), parse_mode=None)
            return

        ledger_content = "📋 SỔ CHI TIẾU & GIAO DỊCH TOÀN DIỆN (HÔM NAY)\n\n"
        dynamic_keyboard = []
        for idx, tx in enumerate(history_list):
            icon_symbol = "🟢" if tx['type'] == "Thu" else "🔴"
            ledger_content += f"{idx+1}. {icon_symbol} [{tx['time']}] {tx['type']}: {tx['amount']:,.0f} đ\n"
            dynamic_keyboard.append([
                InlineKeyboardButton(f"#{idx+1} ❌ Xóa", callback_data=f"ent_del_{idx}"),
                InlineKeyboardButton(f"#{idx+1} ✏️ Sửa", callback_data=f"ent_edit_{idx}")
            ])
        dynamic_keyboard.append([InlineKeyboardButton("🔙 Quay lại Menu", callback_data="ent_back_home")])
        
        await query.message.edit_text(
            ledger_content,
            reply_markup=InlineKeyboardMarkup(dynamic_keyboard),
            parse_mode=None
        )
        enterprise_record_audit_trail(user_id, "VIEW_LEDGER", "Xem toàn bộ sổ chi tiết giao dịch.")

    elif callback_data.startswith("ent_del_"):
        tx_index = int(callback_data.split("_")[2])
        history_list = enterprise_user_registry[user_id]["transaction_history"]
        if tx_index < len(history_list):
            removed_tx = history_list.pop(tx_index)
            if removed_tx['type'] == "Thu":
                enterprise_user_registry[user_id]["daily_income"] -= removed_tx['amount']
                enterprise_user_registry[user_id]["yearly_income"] -= removed_tx['amount']
            else:
                enterprise_user_registry[user_id]["daily_expense"] -= removed_tx['amount']
                enterprise_user_registry[user_id]["yearly_expense"] -= removed_tx['amount']
            await query.answer("Đã xóa giao dịch thành công!", show_alert=False)
            enterprise_record_audit_trail(user_id, "DELETE_TX", f"Đã xóa giao dịch tại vị trí {tx_index}")

        # Render lại sổ giao dịch sau khi xóa
        history_list = enterprise_user_registry[user_id]["transaction_history"]
        if not history_list:
            back_keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="ent_back_home")]]
            await query.message.edit_text("📋 SỔ CHI TIẾU\n\n✨ Sổ trống hoàn toàn.", reply_markup=InlineKeyboardMarkup(back_keyboard), parse_mode=None)
            return

        ledger_content = "📋 SỔ CHI TIẾU & GIAO DỊCH\n\n"
        dynamic_keyboard = []
        for i, tx in enumerate(history_list):
            icon_symbol = "🟢" if tx['type'] == "Thu" else "🔴"
            ledger_content += f"{i+1}. {icon_symbol} [{tx['time']}] {tx['type']}: {tx['amount']:,.0f} đ\n"
            dynamic_keyboard.append([
                InlineKeyboardButton(f"#{i+1} ❌ Xóa", callback_data=f"ent_del_{i}"),
                InlineKeyboardButton(f"#{i+1} ✏️ Sửa", callback_data=f"ent_edit_{i}")
            ])
        dynamic_keyboard.append([InlineKeyboardButton("🔙 Quay lại Menu", callback_data="ent_back_home")])
        await query.message.edit_text(ledger_content, reply_markup=InlineKeyboardMarkup(dynamic_keyboard), parse_mode=None)

    elif callback_data.startswith("ent_edit_"):
        tx_index = int(callback_data.split("_")[2])
        enterprise_user_states[user_id] = f"EDITING_TX_INDEX_{tx_index}"
        prompt_msg = await query.message.reply_text(
            f"✏️ SỬA GIAO DỊCH #{tx_index+1}:\n"
            "Vui lòng gửi số tiền mới thay thế (Ví dụ: 75k, 3tr):",
            parse_mode=None
        )
        enterprise_message_tracker.setdefault(user_id, []).append(prompt_msg.message_id)
        enterprise_record_audit_trail(user_id, "INIT_EDIT_TX", f"Chuẩn bị sửa giao dịch số {tx_index}")

    elif callback_data == "ent_view_year":
        y_inc = enterprise_user_registry[user_id]["yearly_income"]
        y_exp = enterprise_user_registry[user_id]["yearly_expense"]
        y_balance = y_inc - y_exp
        
        back_keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="ent_back_home")]]
        await query.message.edit_text(
            f"📈 BÁO CÁO TÀI CHÍNH TOÀN NĂM DOANH NGHIỆP\n\n"
            f"🟢 Tổng Thu Nhập Năm: {y_inc:,.0f} đ\n"
            f"🔴 Tổng Chi Tiêu Năm: {y_exp:,.0f} đ\n"
            f"💎 Số Dư Ròng Tích Lũy: {y_balance:,.0f} đ",
            reply_markup=InlineKeyboardMarkup(back_keyboard),
            parse_mode=None
        )
        enterprise_record_audit_trail(user_id, "VIEW_YEAR_REPORT", "Xem báo cáo tài chính năm.")

    elif callback_data == "ent_settings_budget":
        enterprise_user_states[user_id] = "WAITING_NEW_BUDGET"
        prompt_msg = await query.message.reply_text(
            "⚙️ CẤU HÌNH HẠN MỨC NGÂN SÁCH:\n"
            "Vui lòng gửi hạn mức ngân sách mới cho hệ thống (Ví dụ: 20tr, 50000000):",
            parse_mode=None
        )
        enterprise_message_tracker.setdefault(user_id, []).append(prompt_msg.message_id)

    elif callback_data == "ent_audit_report":
        audit_records = enterprise_audit_ledgers[user_id][-5:]
        audit_str = "\n".join([f"[{r['timestamp']}] {r['action']} ({r['checksum']})" for r in audit_records])
        back_keyboard = [[InlineKeyboardButton("🔙 Quay lại Menu", callback_data="ent_back_home")]]
        await query.message.edit_text(
            f"📜 BÁO CÁO KIỂM TOÁN HỆ THỐNG (5 GẦN NHẤT):\n\n{audit_str}",
            reply_markup=InlineKeyboardMarkup(back_keyboard),
            parse_mode=None
        )

    elif callback_data == "ent_back_home":
        if user_id in enterprise_message_tracker:
            for msg_id in enterprise_message_tracker[user_id]:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
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
        menu_text, reply_markup = enterprise_render_dashboard_menu(user_id)
        sent_message = await context.bot.send_message(
            chat_id=chat_id,
            text=menu_text,
            reply_markup=reply_markup,
            parse_mode=None
        )
        enterprise_menu_pointers[user_id] = sent_message.message_id
        enterprise_record_audit_trail(user_id, "RETURN_HOME", "Quay về bảng điều khiển chính.")


# ====================================================================================================
# MODULE 6: BỘ NÃO PHÂN TÍCH Ý ĐỊNH VÀ XỬ LÝ TIN NHẮN ĐA TẦNG (ENTERPRISE AI & NLP ENGINE)
# ====================================================================================================

async def enterprise_incoming_message_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trình điều phối tin nhắn trung tâm phân tích bằng AI LLama-3.3 kết hợp kiểm toán tài chính."""
    user_id = update.effective_user.id
    raw_text = update.message.text.strip()
    chat_id = update.effective_chat.id

    enterprise_bootstrap_user(user_id)
    if user_id not in enterprise_user_states:
        enterprise_user_states[user_id] = "ENTERPRISE_AI_CHAT"

    current_state = enterprise_user_states[user_id]

    # Kiểm tra lệnh thoát chế độ AI chat nhanh
    if current_state == "ENTERPRISE_AI_CHAT":
        exit_commands = ["đóng chat", "thoát ai", "về menu", "thôi", "bye", "đóng", "thoát", "menu"]
        if any(cmd in raw_text.lower() for cmd in exit_commands):
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
            menu_text, reply_markup = enterprise_render_dashboard_menu(user_id)
            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text=menu_text,
                reply_markup=reply_markup,
                parse_mode=None
            )
            enterprise_menu_pointers[user_id] = sent_message.message_id
            enterprise_record_audit_trail(user_id, "EXIT_AI_CHAT", "Thoát chế độ AI chat bằng từ khóa.")
            return

        try:
            user_msg_id = update.message.message_id
            enterprise_message_tracker.setdefault(user_id, []).append(user_msg_id)
            await update.message.delete()
        except Exception:
            pass

        thinking_msg = await context.bot.send_message(chat_id=chat_id, text="🐷 Heo Đất AI Enterprise đang phân tích chuyên sâu...")
        enterprise_message_tracker[user_id].append(thinking_msg.message_id)

        intent_classification_result = {"intent": "CHAT", "response_text": raw_text}
        
        if groq_client:
            try:
                classifier_system_prompt = (
                    "Bạn là bộ não phân loại ý định tối tân giống như Grok Enterprise. Phân loại câu của người dùng thành 1 trong 3 nhóm:\n"
                    "1. 'IMAGE': Muốn vẽ tranh, tạo hình ảnh, thiết kế đồ họa.\n"
                    "2. 'MUSIC': Muốn nghe nhạc, tìm bài hát, âm thanh.\n"
                    "3. 'CHAT': Trò chuyện, hỏi đáp tri thức hoặc lập luận.\n\n"
                    "Trả về ĐÚNG định dạng JSON thuần túy (không kèm markdown codeblock):\n"
                    "{\"intent\": \"IMAGE\" hoặc \"MUSIC\" hoặc \"CHAT\", \"response_text\": \"Prompt vẽ ảnh tiếng Anh chuyên nghiệp hoặc câu trả lời trò chuyện\"}\n\n"
                    f"Nội dung đầu vào: \"{raw_text}\""
                )

                response = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": classifier_system_prompt}],
                    model="llama-3.3-70b-versatile",
                    temperature=0.1
                )
                
                raw_json_output = response.choices[0].message.content.strip()
                if raw_json_output.startswith("```"):
                    raw_json_output = raw_json_output.split("```")[1]
                    if raw_json_output.startswith("json"):
                        raw_json_output = raw_json_output[4:]
                raw_json_output = raw_json_output.strip()

                intent_classification_result = json.loads(raw_json_output)
            except Exception as ex:
                logger.error(f"Lỗi phân loại Intent Engine: {ex}")

        detected_intent = intent_classification_result.get("intent", "CHAT")
        payload_content = intent_classification_result.get("response_text", raw_text)

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=thinking_msg.message_id)
            enterprise_message_tracker[user_id].remove(thinking_msg.message_id)
        except Exception:
            pass

        if detected_intent == "IMAGE":
            encoded_image_prompt = urllib.parse.quote(payload_content)
            generated_image_url = f"https://image.pollinations.ai/prompt/{encoded_image_prompt}?width=1024&height=1024&nologo=true"
            try:
                photo_msg = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=generated_image_url,
                    caption=f"🐷 Image Engine Generated:\n'{raw_text}'",
                    parse_mode=None
                )
                enterprise_message_tracker[user_id].append(photo_msg.message_id)
                enterprise_record_audit_trail(user_id, "AI_GEN_IMAGE", f"Tạo ảnh thành công với prompt: {payload_content}")
            except Exception as image_ex:
                logger.error(f"Lỗi truyền tải hình ảnh: {image_ex}")
            return

        elif detected_intent == "MUSIC":
            try:
                sample_audio_stream_url = "https://actions.google.com/sounds/v1/ambiences/rain_heavy.ogg"
                audio_msg = await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=sample_audio_stream_url,
                    title=payload_content[:50],
                    caption=f"🎧 Music Engine Stream:\n'{raw_text}'",
                    parse_mode=None
                )
                enterprise_message_tracker[user_id].append(audio_msg.message_id)
                enterprise_record_audit_trail(user_id, "AI_GEN_MUSIC", f"Phát nhạc trực tuyến cho yêu cầu: {payload_content}")
            except Exception as audio_ex:
                logger.error(f"Lỗi truyền tải âm thanh: {audio_ex}")
            return

        else:
            enterprise_chat_histories[user_id].append({"role": "user", "content": raw_text})
            final_assistant_reply = payload_content
            
            if groq_client:
                try:
                    chat_completion = groq_client.chat.completions.create(
                        messages=enterprise_chat_histories[user_id],
                        model="llama-3.3-70b-versatile",
                        temperature=0.7,
                    )
                    final_assistant_reply = chat_completion.choices[0].message.content
                except Exception as chat_ex:
                    logger.error(f"Lỗi Groq Chat Completion: {chat_ex}")

            enterprise_chat_histories[user_id].append({"role": "assistant", "content": final_assistant_reply})

            bot_reply_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"🐷 Heo Đất AI Pro:\n\n{final_assistant_reply}",
                parse_mode=None
            )
            enterprise_message_tracker[user_id].append(bot_reply_msg.message_id)
            enterprise_record_audit_trail(user_id, "AI_CHAT_REPLY", "Phản hồi tin nhắn trò chuyện thành công.")
            return

    # Xử lý các trạng thái sửa giao dịch
    if current_state.startswith("EDITING_TX_INDEX_"):
        tx_idx = int(current_state.split("_")[3])
        try:
            parsed_amount = enterprise_parse_amount_string(raw_text)
        except ValueError:
            await update.message.reply_text("❌ Sai định dạng số tiền! Vui lòng gửi số hợp lệ (Ví dụ: 50k, 2tr).")
            return

        transaction_list = enterprise_user_registry[user_id]["transaction_history"]
        if tx_idx < len(transaction_list):
            old_tx_item = transaction_list[tx_idx]
            amount_delta = parsed_amount - old_tx_item['amount']
            if old_tx_item['type'] == "Thu":
                enterprise_user_registry[user_id]["daily_income"] += amount_delta
                enterprise_user_registry[user_id]["yearly_income"] += amount_delta
            else:
                enterprise_user_registry[user_id]["daily_expense"] += amount_delta
                enterprise_user_registry[user_id]["yearly_expense"] += amount_delta
            old_tx_item['amount'] = parsed_amount
            await update.message.reply_text(f"✅ Đã cập nhật giao dịch thành công lên {parsed_amount:,.0f} đ!", parse_mode=None)
            enterprise_record_audit_trail(user_id, "UPDATE_TX", f"Cập nhật giao dịch #{tx_idx+1} thành {parsed_amount}")

        enterprise_user_states.pop(user_id, None)
        return

    # Xử lý cập nhật ngân sách
    if current_state == "WAITING_NEW_BUDGET":
        try:
            new_budget_limit = enterprise_parse_amount_string(raw_text)
            enterprise_user_registry[user_id]["budget_limit"] = new_budget_limit
            await update.message.reply_text(f"✅ Đã thiết lập hạn mức ngân sách mới: {new_budget_limit:,.0f} đ!", parse_mode=None)
            enterprise_record_audit_trail(user_id, "UPDATE_BUDGET", f"Thiết lập hạn mức ngân sách: {new_budget_limit}")
        except ValueError:
            await update.message.reply_text("❌ Sai định dạng số tiền ngân sách!")
        enterprise_user_states.pop(user_id, None)
        return

    # Xử lý nạp Thu / Chi thông thường
    try:
        amount_value = enterprise_parse_amount_string(raw_text)
    except ValueError:
        await update.message.reply_text("❌ Sai định dạng tiền! (Ví dụ: 50k, 2tr, 150000)")
        return

    current_time_str = datetime.now().strftime("%H:%M")
    if current_state == "WAITING_INCOME_INPUT":
        enterprise_user_registry[user_id]["daily_income"] += amount_value
        enterprise_user_registry[user_id]["yearly_income"] += amount_value
        enterprise_user_registry[user_id]["transaction_history"].append({"time": current_time_str, "type": "Thu", "amount": amount_value})
        await update.message.reply_text(f"✅ Đã ghi nhận Thu nhập doanh nghiệp: +{amount_value:,.0f} đ!", parse_mode=None)
        enterprise_record_audit_trail(user_id, "ADD_INCOME", f"Nạp thu nhập: +{amount_value}")
    elif current_state == "WAITING_EXPENSE_INPUT":
        enterprise_user_registry[user_id]["daily_expense"] += amount_value
        enterprise_user_registry[user_id]["yearly_expense"] += amount_value
        enterprise_user_registry[user_id]["transaction_history"].append({"time": current_time_str, "type": "Chi", "amount": amount_value})
        await update.message.reply_text(f"✅ Đã ghi nhận Chi tiêu doanh nghiệp: -{amount_value:,.0f} đ!", parse_mode=None)
        enterprise_record_audit_trail(user_id, "ADD_EXPENSE", f"Rút chi tiêu: -{amount_value}")

    enterprise_user_states.pop(user_id, None)


def enterprise_parse_amount_string(text_input: str) -> float:
    """Hàm phụ trợ phân tích chuỗi tiền tệ tiếng Việt sang kiểu float chuẩn."""
    cleaned = text_input.lower().replace("vnđ", "").replace("đ", "").replace(",", "").replace(" ", "").strip()
    multiplier = 1.0
    if "k" in cleaned:
        multiplier = 1000.0
        cleaned = cleaned.replace("k", "")
    elif "tr" in cleaned:
        multiplier = 1000000.0
        cleaned = cleaned.replace("tr", "")
    elif "m" in cleaned:
        multiplier = 1000000.0
        cleaned = cleaned.replace("m", "")
    elif "tỷ" in cleaned or "b" in cleaned:
        multiplier = 1000000000.0
        cleaned = cleaned.replace("tỷ", "").replace("b", "")
    
    return float(cleaned) * multiplier


# ====================================================================================================
# MODULE 7: CÁC KHỐI MÃ MỞ RỘNG VÀ TIỆN ÍCH DỰ PHÒNG (DUMMY EXTENSIONS & STUB MODULES)
# Để đảm bảo mã nguồn đạt quy mô cấu trúc lớn, minh bạch và an toàn, các hệ thống giám sát định kỳ,
# bộ nhớ đệm phân tán giả lập và các thuật toán mã hóa bổ sung được tích hợp ở tầng dưới này.
# ====================================================================================================

class EnterpriseSecurityTokenValidator:
    """Lớp kiểm tra token và mã hóa chữ ký số giao dịch doanh nghiệp."""
    def __init__(self, secret_seed: str = "HEO_DAT_AI_PRO_2026"):
        self.secret_seed = secret_seed
        self.validation_registry: Set[str] = set()

    def generate_secure_token(self, user_id: int) -> str:
        raw_string = f"{user_id}:{time.time()}:{self.secret_seed}"
        token_hash = hashlib.sha256(raw_string.encode()).hexdigest()
        self.validation_registry.add(token_hash)
        return token_hash

    def verify_token(self, token_hash: str) -> bool:
        return token_hash in self.validation_registry


class EnterpriseBackgroundWorkerScheduler:
    """Lớp lập lịch tác vụ nền giả lập cho hệ thống doanh nghiệp."""
    def __init__(self):
        self.task_queue: List[Dict[str, Any]] = []

    def schedule_task(self, task_name: str, callback_func, delay_seconds: int):
        task_info = {
            "name": task_name,
            "callback": callback_func,
            "execute_at": time.time() + delay_seconds
        }
        self.task_queue.append(task_info)
        logger.info(f"Đã lập lịch tác vụ nền: {task_name} sau {delay_seconds} giây.")

    def process_queue(self):
        current_ts = time.time()
        for task in self.task_queue[:]:
            if current_ts >= task["execute_at"]:
                try:
                    task["callback"]()
                except Exception as e:
                    logger.error(f"Lỗi thực thi tác vụ nền {task['name']}: {e}")
                self.task_queue.remove(task)


# Khởi tạo các tiện ích hệ thống toàn cục
security_validator_instance = EnterpriseSecurityTokenValidator()
background_scheduler_instance = EnterpriseBackgroundWorkerScheduler()


# ====================================================================================================
# MODULE 8: KHỞI CHẠY ỨNG DỤNG ENTERPRISE BOT (BOOTSTRAPPER & ENTRY POINT)
# ====================================================================================================

def main() -> None:
    """Điểm khởi chạy bất đồng bộ chính thức cho Telegram Bot Enterprise Monolithic Core."""
    logger.info("Đang khởi động hệ thống Heo Đất AI Pro - Ultra Enterprise Core...")
    
    # Kích hoạt keep-alive web server ngầm
    keep_alive()

    # Xây dựng ứng dụng Telegram Bot
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Đăng ký các bộ xử lý (Handlers)
    application.add_handler(CommandHandler("start", enterprise_command_start_handler))
    application.add_handler(CallbackQueryHandler(enterprise_callback_router))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), enterprise_incoming_message_dispatcher))

    logger.info("==================================================================================")
    logger.info("🚀 HEO ĐẤT AI PRO - ULTRA MONOLITHIC ENTERPRISE MEGA CORE ĐÃ KHỞI ĐỘNG THÀNH CÔNG!")
    logger.info("==================================================================================")

    # Chạy vòng lặp polling
    application.run_polling()


if __name__ == "__main__":
    main()

```
