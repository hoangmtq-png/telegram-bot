"""
BOT SHOP BÁN ACC GAME (Delta Force / Free Fire / Liên Quân)  -  BẢN NÂNG CẤP
- Menu chính hiện đại: 3 game nằm NGAY TRÊN MENU (bấm là vào danh sách acc)
- Khách: xem acc (bot gửi ảnh), mua bằng số dư, nạp tiền QR (theo số tiền chọn), xem lịch sử
- Nạp tự động: SePay webhook -> cộng tiền theo nội dung "NAP<ID Telegram>"
- Admin: danh sách khách & số dư, cộng/trừ tiền, thêm/xoá acc, broadcast, gửi tin riêng, thống kê
- Tự xoá tin rác, bấm tác vụ mới thì tin cũ biến mất
- TỰ SAO LƯU database vào Telegram (ghim trong chat admin) và TỰ KHÔI PHỤC khi khởi động
Yêu cầu: pip install -r requirements.txt  (aiogram, flask, waitress, segno)
"""
import asyncio, hmac, html, io, json, logging, os, re, sqlite3, threading, time
import urllib.request
from urllib.parse import quote

from flask import Flask, jsonify, request
from waitress import serve
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.methods import SendDocument, SendMediaGroup, SendMessage, SendPhoto
from aiogram.types import (BufferedInputFile, CallbackQuery, ErrorEvent, FSInputFile,
                           InputMediaPhoto, Message)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ============================ CẤU HÌNH ============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()


def _parse_admin_ids(raw: str) -> set:
    ids = set()
    for x in re.split(r"[,\s;]+", raw or ""):
        if x.isdigit():
            ids.add(int(x))
        elif x:
            print(f"[CẢNH BÁO] ADMIN_IDS có giá trị không hợp lệ: {x!r} - phải là ID dạng SỐ (lấy ở @userinfobot)")
    return ids


ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
BANK_CODE = "MB"
BANK_BIN = "970422"   # MB = 970422, VCB = 970436, ACB = 970416, TCB = 970407, BIDV = 970418, VietinBank = 970415
BANK_ACCOUNT = "3030777777"
BANK_OWNER = "NGUYEN TIEN DAT"
SHOP_NAME = "SHOP ACC GAME"
SEPAY_API_KEY = os.getenv("SEPAY_API_KEY", "")
WEBHOOK_PORT = int(os.getenv("PORT", "8080"))
SUPPORT = os.getenv("SUPPORT", "@your_username")
DB_FILE = os.getenv("DB_FILE", "shop.db")   # Render Disk: đặt DB_FILE=/data/shop.db
DB_TEMP = False
_db_dir = os.path.dirname(DB_FILE)
if _db_dir and not os.path.isdir(_db_dir):
    DB_FILE = "shop.db"
    DB_TEMP = True

GAMES = {
    "delta": "🎯 Delta Force",
    "ff": "🔥 Free Fire",
    "lq": "⚔️ Liên Quân",
}

VIP_LEVELS = [0, 1, 2, 3, 4, 5]
PRICE_PRESETS = [
    ("Tất cả", 0, 0),
    ("Dưới 50K", 0, 50000),
    ("50K-100K", 50000, 100000),
    ("100K-200K", 100000, 200000),
    ("200K-500K", 200000, 500000),
    ("Trên 500K", 500000, 0),
]
MIN_DEPOSIT = 10000
MAX_DEPOSIT = 500_000_000
# ==================================================================

logging.basicConfig(level=logging.INFO)
router = Router()

# ----------------------- KHÔI PHỤC DATABASE TỪ TELEGRAM -----------------------
AUTO_BACKUP = os.getenv("AUTO_BACKUP", "1") != "0"
RESTORE_STATUS = "skip"   # skip | restored | none | error


def restore_from_telegram() -> str:
    """Container mới (mất file DB) -> lấy lại bản sao lưu đang được GHIM trong chat riêng với admin đầu tiên."""
    if not AUTO_BACKUP:
        return "skip"
    if os.path.exists(DB_FILE) and os.path.getsize(DB_FILE) > 0:
        return "skip"
    if not BOT_TOKEN or not ADMIN_IDS:
        return "skip"
    base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    ad = min(ADMIN_IDS)
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(f"{base}/getChat?chat_id={ad}", timeout=20) as r:
                pm = json.load(r)["result"].get("pinned_message")
            doc = (pm or {}).get("document")
            if not doc or not str((pm or {}).get("caption", "")).startswith("💾 AUTO_BACKUP"):
                print("[BACKUP] Chưa có bản sao lưu nào được ghim -> bắt đầu database mới")
                return "none"
            with urllib.request.urlopen(f"{base}/getFile?file_id={doc['file_id']}", timeout=20) as r:
                fpath = json.load(r)["result"]["file_path"]
            with urllib.request.urlopen(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fpath}", timeout=60) as r:
                data = r.read()
            if not data.startswith(b"SQLite format 3"):
                raise ValueError("file sao lưu không phải SQLite")
            with open(DB_FILE, "wb") as f:
                f.write(data)
            print(f"[BACKUP] Đã khôi phục database từ Telegram ({len(data)} bytes)")
            return "restored"
        except Exception as e:
            last_err = e
            time.sleep(2)
    print(f"[BACKUP] LỖI khôi phục database: {last_err!r}")
    return "error"


RESTORE_STATUS = restore_from_telegram()

# ----------------------------- DATABASE -----------------------------
db = sqlite3.connect(DB_FILE, isolation_level=None, check_same_thread=False)
db.row_factory = sqlite3.Row
db.executescript("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY, username TEXT, name TEXT,
    balance INTEGER DEFAULT 0, created INTEGER);
CREATE TABLE IF NOT EXISTS accounts(
    id INTEGER PRIMARY KEY AUTOINCREMENT, game TEXT, title TEXT, price INTEGER,
    info TEXT, login TEXT, photos TEXT, sold INTEGER DEFAULT 0,
    buyer INTEGER, sold_at INTEGER, created INTEGER);
CREATE TABLE IF NOT EXISTS tx(
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
    type TEXT, note TEXT, ref TEXT UNIQUE, created INTEGER);
""")

try:
    db.execute("ALTER TABLE accounts ADD COLUMN vip INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass

db.execute("CREATE INDEX IF NOT EXISTS idx_acc ON accounts(game, sold, price)")


def q(sql, args=()):
    return db.execute(sql, args).fetchall()


def q1(sql, args=()):
    return db.execute(sql, args).fetchone()


def money(n):
    return f"{int(n):,}".replace(",", ".") + "đ"


def esc(s):
    return html.escape(str(s or ""))


def ensure_user(u):
    if not q1("SELECT id FROM users WHERE id=?", (u.id,)):
        db.execute("INSERT INTO users(id,username,name,balance,created) VALUES(?,?,?,?,?)",
                   (u.id, u.username, u.full_name, 0, int(time.time())))
    else:
        db.execute("UPDATE users SET username=?, name=? WHERE id=?", (u.username, u.full_name, u.id))


def balance(uid):
    r = q1("SELECT balance FROM users WHERE id=?", (uid,))
    return r["balance"] if r else 0


def change_balance(uid, amount, typ, note="", ref=None):
    """Cộng (+) / trừ (-) tiền. ref dùng chống cộng trùng giao dịch. Trả về False nếu trùng."""
    if not q1("SELECT id FROM users WHERE id=?", (uid,)):
        db.execute("INSERT INTO users(id,balance,created) VALUES(?,?,?)", (uid, 0, int(time.time())))
    try:
        db.execute("INSERT INTO tx(user_id,amount,type,note,ref,created) VALUES(?,?,?,?,?,?)",
                   (uid, amount, typ, note, ref, int(time.time())))
    except sqlite3.IntegrityError:
        return False
    db.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, uid))
    return True


def is_admin(uid):
    return uid in ADMIN_IDS


# ----------------------------- MENU CHÍNH (HIỆN ĐẠI) -----------------------------
def menu_text(user) -> str:
    status = "Quản Trị Viên" if is_admin(user.id) else "Thành Viên Chính Thức"
    in_stock = q1("SELECT COUNT(*) n FROM accounts WHERE sold=0")["n"]
    return (
        f"✨ <b>HỆ THỐNG {SHOP_NAME} - UY TÍN &amp; TỰ ĐỘNG</b> ✨\n"
        f"══════════════════════\n\n"
        f"👋 Xin chào, <b>{esc(user.full_name)}</b>!\n"
        f"💎 Trạng thái: <b>{status}</b>\n\n"
        f"💳 <b>TÀI KHOẢN CỦA BẠN:</b>\n"
        f"┣ 🆔 ID Telegram: <code>{user.id}</code>\n"
        f"┗ 💰 Số dư hiện tại: <code>{money(balance(user.id))}</code>\n\n"
        f"📦 Kho hiện có: <b>{in_stock}</b> acc đang bán\n"
        f"⚡ Hệ thống hoàn tất xử lý tự động 24/7.\n"
        f"👇 Vui lòng chọn danh mục dịch vụ bên dưới:")


def main_menu(uid):
    b = InlineKeyboardBuilder()
    counts = {r["game"]: r["n"] for r in q("SELECT game, COUNT(*) n FROM accounts WHERE sold=0 GROUP BY game")}
    for key, name in GAMES.items():
        b.button(text=f"{name.upper()} ({counts.get(key, 0)} acc)", callback_data=f"game:{key}")
    b.button(text="💳 NẠP TIỀN AUTO", callback_data="menu:deposit")
    b.button(text="📜 LỊCH SỬ", callback_data="menu:history")
    b.button(text="👤 TÀI KHOẢN", callback_data="menu:balance")
    b.button(text="📖 HƯỚNG DẪN", callback_data="menu:guide")
    b.button(text="💬 HỖ TRỢ KỸ THUẬT (ADMIN)", callback_data="menu:support")
    if is_admin(uid):
        b.button(text="⚙️ ADMIN PANEL", callback_data="adm:home")
    b.adjust(1, 2, 2, 2, 1, 1)
    return b.as_markup()


def back_main():
    b = InlineKeyboardBuilder()
    b.button(text="🏠 Menu Chính", callback_data="menu:main")
    return b.as_markup()


def nav_kb(back_cb="adm:home", back_text="⬅️ Quay lại Admin"):
    b = InlineKeyboardBuilder()
    b.button(text=back_text, callback_data=back_cb)
    b.button(text="🏠 Menu Chính", callback_data="menu:main")
    b.adjust(2)
    return b.as_markup()


def admin_menu():
    b = InlineKeyboardBuilder()
    for t, c in [
        ("👥 Danh Sách Khách & Số Dư", "adm:users"),
        ("💰 Cộng / Trừ Tiền Theo ID", "adm:money"),
        ("➕ Thêm Acc Mới", "adm:add"),
        ("📦 Quản Lý / Xoá Acc", "adm:list"),
        ("📊 Thống Kê Doanh Thu", "adm:stats"),
        ("📖 Hướng Dẫn Admin", "adm:guide"),
        ("📢 Gửi Thông Báo Broadcast", "adm:bc"),
        ("👤 Gửi Tin Riêng (Cá Nhân)", "adm:pm"),
        ("🏠 Menu Chính", "menu:main"),
    ]:
        b.button(text=t, callback_data=c)
    b.adjust(1)
    return b.as_markup()


# ----------------------------- CHẶN KẸT TRẠNG THÁI + BẮT LỖI -----------------------------
async def reset_state_on_command(handler, event, data):
    """Gõ lệnh /... (trừ /done) khi đang nhập dở thì thoát trạng thái nhập.
    Đang ở bước nhập: xoá tin nhắc cũ của bot và xoá luôn tin vừa gõ để khung chat gọn."""
    st = data.get("state")
    t = (getattr(event, "text", None) or "").strip()
    if t.startswith("/"):
        cmd = t.split()[0].split("@")[0].lower()
        if cmd != "/done":
            if st is not None:
                await st.clear()
                data["raw_state"] = None
    tidy = False
    if st is not None and getattr(getattr(event, "chat", None), "type", "") == "private":
        tidy = (await st.get_state()) is not None
    if tidy:
        await wipe_tracked(event.bot, event.chat.id)
    try:
        return await handler(event, data)
    finally:
        if tidy:
            try:
                await event.delete()
            except Exception:
                pass


router.message.outer_middleware(reset_state_on_command)


# ----------------------------- TỰ ĐỘNG XOÁ TIN NHẮN -----------------------------
TRACK = {}
BG_TASKS = set()
TTL_DEFAULT = 60
TTL_MEDIA = 300
TTL_QR = 600
QR_PREFIX = "💳 <b>NẠP TIỀN TỰ ĐỘNG"
KEEP_PREFIXES = ("🎉", "✅ <b>NẠP TIỀN THÀNH CÔNG", "📢", "💬", "💰 Admin", "🛍", "💳 Khách", "⚠️ <b>CẢNH BÁO", "💾")


def _msg_text(method):
    t = getattr(method, "text", None) or getattr(method, "caption", None)
    if not t and isinstance(method, SendMediaGroup):
        for md in method.media:
            if getattr(md, "caption", None):
                return md.caption
    return t or ""


async def _delete_later(bot, chat_id, ids, ttl):
    await asyncio.sleep(ttl)
    for i in ids:
        try:
            await bot.delete_message(chat_id, i)
        except Exception:
            pass
    cur = TRACK.get(chat_id)
    if cur:
        TRACK[chat_id] = [x for x in cur if x not in ids]


async def wipe_tracked(bot, chat_id):
    for i in TRACK.pop(chat_id, []):
        try:
            await bot.delete_message(chat_id, i)
        except Exception:
            pass


class TrackMW(BaseRequestMiddleware):
    """Ghi nhớ mọi tin bot gửi cho khách để tự xoá."""
    async def __call__(self, make_request, bot, method):
        result = await make_request(bot, method)
        try:
            if (isinstance(method, (SendMessage, SendPhoto, SendMediaGroup, SendDocument))
                    and isinstance(method.chat_id, int) and method.chat_id > 0):
                text = _msg_text(method)
                if not text.startswith(KEEP_PREFIXES):
                    msgs = result if isinstance(result, list) else [result]
                    ids = [x.message_id for x in msgs]
                    if isinstance(method, SendMediaGroup):
                        ttl = TTL_MEDIA
                    elif text.startswith(QR_PREFIX):
                        ttl = TTL_QR
                    elif getattr(method, "reply_markup", None):
                        ttl = None
                    else:
                        ttl = TTL_DEFAULT
                    lst = TRACK.setdefault(method.chat_id, [])
                    lst.extend(ids)
                    del lst[:-40]
                    if ttl:
                        t = asyncio.create_task(_delete_later(bot, method.chat_id, ids, ttl))
                        BG_TASKS.add(t)
                        t.add_done_callback(BG_TASKS.discard)
        except Exception:
            logging.exception("TrackMW lỗi")
        return result


async def clean_on_callback(handler, event, data):
    """Khách bấm nút -> xoá các tin cũ của bot phía trên (trừ tin quan trọng)."""
    d = event.data or ""
    edits_current = (d.startswith(("f:", "am:", "del:", "delc:", "pv:", "st:", "stc:"))
                     or bool(re.match(r"adm:list:\d", d)))
    keep_id = event.message.message_id if (event.message and edits_current) else None
    ids = TRACK.pop(event.from_user.id, [])
    survivors = []
    for i in ids:
        if i == keep_id:
            survivors.append(i)
            continue
        try:
            await event.bot.delete_message(event.from_user.id, i)
        except Exception:
            pass
    if survivors:
        TRACK[event.from_user.id] = survivors
    return await handler(event, data)


router.callback_query.outer_middleware(clean_on_callback)


@router.message(Command("huy"))
async def cmd_cancel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("✅ Đã huỷ thao tác.", reply_markup=main_menu(m.from_user.id))


@router.error()
async def on_error(event: ErrorEvent):
    logging.error("Lỗi khi xử lý update: %r", event.exception, exc_info=event.exception)
    try:
        u = event.update
        if u.callback_query:
            await u.callback_query.answer("⚠️ Có lỗi xảy ra, vui lòng thử lại.", show_alert=True)
        elif u.message:
            await u.message.answer("⚠️ Có lỗi xảy ra, vui lòng thử lại hoặc gõ /start.")
    except Exception:
        pass
    return True


# ----------------------------- KHÁCH HÀNG -----------------------------
async def send_main_menu(target: Message, user):
    ensure_user(user)
    await target.answer(menu_text(user), reply_markup=main_menu(user.id))


@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await send_main_menu(m, m.from_user)


@router.message(Command("menu"))
async def cmd_menu(m: Message, state: FSMContext):
    await state.clear()
    await send_main_menu(m, m.from_user)


@router.callback_query(F.data == "menu:main")
async def cb_main(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await send_main_menu(c.message, c.from_user)
    await c.answer()


@router.callback_query(F.data == "menu:shop")
async def cb_shop(c: CallbackQuery, state: FSMContext):
    """Tương thích nút cũ: game đã nằm ngay trên menu chính."""
    await state.clear()
    await send_main_menu(c.message, c.from_user)
    await c.answer()


@router.callback_query(F.data == "menu:balance")
async def cb_balance(c: CallbackQuery):
    ensure_user(c.from_user)
    await c.message.answer(
        f"👤 <b>TÀI KHOẢN</b>\n┣ 🆔 ID: <code>{c.from_user.id}</code>\n"
        f"┗ 💰 Số dư: <b>{money(balance(c.from_user.id))}</b>",
        reply_markup=back_main())
    await c.answer()


@router.callback_query(F.data == "menu:support")
async def cb_support(c: CallbackQuery):
    await c.message.answer(f"🆘 Cần hỗ trợ liên hệ: {esc(SUPPORT)}", reply_markup=back_main())
    await c.answer()


@router.callback_query(F.data == "menu:history")
async def cb_history(c: CallbackQuery):
    uid = c.from_user.id
    rows = q("SELECT * FROM tx WHERE user_id=? ORDER BY id DESC LIMIT 15", (uid,))
    if not rows:
        text = "📜 Bạn chưa có giao dịch nào."
    else:
        lines = []
        for r in rows:
            sign = "+" if r["amount"] > 0 else ""
            when = time.strftime("%d/%m %H:%M", time.localtime(r["created"]))
            lines.append(f"{when} | {sign}{money(r['amount'])} | {esc(r['note'] or r['type'])}")
        text = "📜 <b>15 GIAO DỊCH GẦN NHẤT</b>\n\n" + "\n".join(lines)
    bought = q("SELECT id,game,title,price FROM accounts WHERE buyer=? AND sold=1 ORDER BY sold_at DESC, id DESC LIMIT 20", (uid,))
    b = InlineKeyboardBuilder()
    if bought:
        text += "\n\n🛍 <b>ACC ĐÃ MUA</b> - bấm vào acc để xem lại tài khoản &amp; mật khẩu:"
        for r in bought:
            b.button(text=f"🔐 #{r['id']} • {GAMES.get(r['game'], '')[:2]} {r['title'][:20]} • {money(r['price'])}",
                     callback_data=f"myacc:{r['id']}")
    b.button(text="🏠 Menu Chính", callback_data="menu:main")
    b.adjust(1)
    await c.message.answer(text, reply_markup=b.as_markup())
    await c.answer()


@router.callback_query(F.data.startswith("myacc:"))
async def cb_my_acc(c: CallbackQuery):
    aid = int(c.data.split(":")[1])
    a = q1("SELECT * FROM accounts WHERE id=? AND buyer=? AND sold=1", (aid, c.from_user.id))
    if not a:
        return await c.answer("Bạn không sở hữu acc này!", show_alert=True)
    when = time.strftime("%d/%m/%Y %H:%M", time.localtime(a["sold_at"] or 0))
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Quay lại lịch sử", callback_data="menu:history")
    b.button(text="🏠 Menu Chính", callback_data="menu:main")
    b.adjust(1)
    await c.message.answer(
        f"🔐 <b>THÔNG TIN ACC #{a['id']}</b>\n"
        f"{GAMES.get(a['game'], a['game'])} • VIP {a['vip'] or 0}\n"
        f"📝 {esc(a['title'])}\n"
        f"💵 Đã mua: <b>{money(a['price'])}</b> lúc {when}\n\n"
        f"👤 Tài khoản | mật khẩu:\n<code>{esc(a['login'])}</code>\n\n"
        f"⚠️ Nên đổi mật khẩu &amp; liên kết ngay. Có vấn đề hãy liên hệ Hỗ Trợ kèm mã #{a['id']}.",
        reply_markup=b.as_markup())
    await c.answer()


# ---- Hướng dẫn sử dụng (khách) ----
GUIDES = {
    "buy": ("🛒 Cách xem & mua acc",
            "🛒 <b>CÁCH XEM &amp; MUA ACC</b>\n\n"
            "1️⃣ Ở menu chính bấm thẳng vào game bạn cần (Delta Force / Free Fire / Liên Quân)\n"
            "2️⃣ Chọn acc trong danh sách. Bot sẽ gửi <b>ảnh + mô tả + giá</b> của đúng acc đó\n"
            "3️⃣ Ưng acc thì bấm <b>✅ MUA NGAY</b>\n"
            "4️⃣ Nếu đủ số dư, bot trừ tiền và <b>gửi ngay tài khoản, mật khẩu</b> cho bạn\n\n"
            "🟢 = còn hàng • ❌ ĐÃ BÁN = đã có người mua (chỉ xem tham khảo)\n"
            "💡 Thiếu tiền thì bot sẽ báo và có nút nạp tiền nhanh."),
    "filter": ("🔎 Cách lọc theo giá & VIP",
               "🔎 <b>CÁCH LỌC ACC THEO GIÁ &amp; VIP</b>\n\n"
               "Sau khi chọn game, bạn sẽ thấy các nút lọc:\n\n"
               "💵 <b>Lọc giá</b>: bấm khoảng giá có sẵn (Dưới 50K, 50K-100K...).\n"
               "   Muốn khoảng giá riêng bấm <b>✍️ Tự nhập giá</b> rồi gõ dạng <code>từ-đến</code>:\n"
               "   • <code>50k-200k</code> • <code>1tr-3tr</code> • <code>100k-</code> (từ 100k trở lên)\n\n"
               "⭐ <b>Lọc VIP</b>: bấm <b>VIP 0, VIP 1...</b> Có thể bấm nhiều mức cùng lúc. "
               "Bấm <b>Mọi VIP</b> để bỏ lọc.\n\n"
               "📄 Danh sách dài thì dùng nút <b>◀️ Trước / Sau ▶️</b> để chuyển trang.\n"
               "✅ Nút có dấu tích là bộ lọc đang chọn."),
    "deposit": ("💳 Cách nạp tiền",
                "💳 <b>CÁCH NẠP TIỀN (TỰ ĐỘNG 24/7)</b>\n\n"
                "1️⃣ Bấm <b>💳 Nạp Tiền Auto</b> ở menu chính, bot gửi ngay <b>mã QR</b>\n"
                "2️⃣ Bấm nút số tiền (20K, 50K, 100K...) hoặc <b>✍️ Nhập số khác</b> "
                "→ bot tạo QR <b>có sẵn số tiền + nội dung</b>, bạn chỉ việc quét và xác nhận\n"
                "3️⃣ Chuyển khoản xong chờ <b>1-2 phút</b>, bot tự cộng tiền và nhắn báo cho bạn\n\n"
                f"🏦 MB Bank • STK <code>{BANK_ACCOUNT}</code> • {BANK_OWNER}\n"
                "⚠️ <b>Giữ nguyên nội dung chuyển khoản</b> <code>NAP + ID Telegram của bạn</code> "
                "(VD <code>NAP123456789</code>). Sai/mất nội dung thì bot không nhận ra bạn.\n"
                "❗ Quá 10 phút chưa thấy cộng tiền: bấm Hỗ Trợ và gửi kèm ảnh bill chuyển khoản."),
    "account": ("👤 Số dư & lịch sử",
                "👤 <b>XEM SỐ DƯ &amp; LỊCH SỬ</b>\n\n"
                "• <b>👤 Tài Khoản</b>: xem ID Telegram và số dư hiện tại\n"
                "• <b>📜 Lịch Sử</b>: xem 15 giao dịch gần nhất và <b>xem lại tài khoản, mật khẩu các acc đã mua</b>\n\n"
                "🆔 ID Telegram của bạn cũng chính là mã dùng trong nội dung chuyển khoản <code>NAP...</code>."),
    "after": ("🔐 Sau khi mua acc",
              "🔐 <b>SAU KHI MUA ACC</b>\n\n"
              "• Bot gửi tài khoản + mật khẩu ngay trong tin nhắn mua thành công. "
              "Hãy <b>copy và lưu lại</b> ngay.\n"
              "• Đăng nhập xong nên <b>đổi mật khẩu</b> và liên kết thông tin của bạn để bảo mật.\n"
              "• Mỗi acc chỉ bán <b>1 lần duy nhất</b> cho 1 người.\n"
              "• Acc có vấn đề hãy liên hệ Hỗ Trợ ngay, kèm <b>mã acc (#số)</b> và ảnh chụp lỗi."),
}


def guide_menu():
    b = InlineKeyboardBuilder()
    for k, (title, _) in GUIDES.items():
        b.button(text=title, callback_data=f"guide:{k}")
    b.button(text="🏠 Menu Chính", callback_data="menu:main")
    b.adjust(1)
    return b.as_markup()


@router.message(Command("huongdan", "help"))
async def cmd_guide(m: Message):
    await m.answer("📖 <b>HƯỚNG DẪN SỬ DỤNG</b>\nChọn mục bạn cần xem:", reply_markup=guide_menu())


@router.callback_query(F.data == "menu:guide")
async def cb_guide(c: CallbackQuery):
    await c.message.answer("📖 <b>HƯỚNG DẪN SỬ DỤNG</b>\nChọn mục bạn cần xem:", reply_markup=guide_menu())
    await c.answer()


@router.callback_query(F.data.startswith("guide:"))
async def cb_guide_item(c: CallbackQuery):
    key = c.data.split(":")[1]
    if key not in GUIDES:
        return await c.answer()
    b = InlineKeyboardBuilder()
    b.button(text="📖 Các hướng dẫn khác", callback_data="menu:guide")
    b.button(text="🏠 Menu Chính", callback_data="menu:main")
    b.adjust(1)
    await c.message.answer(GUIDES[key][1], reply_markup=b.as_markup())
    await c.answer()


# ---- Bộ lọc acc theo GIÁ + VIP ----
USER_FILTER = {}


class PriceIn(StatesGroup):
    rng = State()


def to_vnd(t: str) -> int:
    t = t.strip().lower().replace(" ", "")
    if not t:
        return 0
    if t.endswith("tr"):
        return int(float(t[:-2].replace(",", ".")) * 1_000_000)
    if t.endswith("k"):
        return int(float(t[:-1].replace(",", ".")) * 1_000)
    return int(re.sub(r"\D", "", t) or 0)


def vip_text(mask: int) -> str:
    if not mask:
        return "Tất cả"
    return ", ".join(f"VIP {v}" for v in VIP_LEVELS if mask >> v & 1)


def price_text(lo: int, hi: int) -> str:
    if not lo and not hi:
        return "Tất cả"
    if not hi:
        return f"Từ {money(lo)} trở lên"
    return f"{money(lo)} → {money(hi)}"


PAGE_SIZE = 8


async def show_filter(target: Message, uid: int, game: str, rng: str, mask: int, page: int = 0, edit: bool = False):
    lo, hi = (int(x) for x in rng.split("-"))
    where = "game=? AND price>=?"
    args = [game, lo]
    if hi:
        where += " AND price<=?"
        args.append(hi)
    if mask:
        levels = [v for v in VIP_LEVELS if mask >> v & 1]
        where += f" AND COALESCE(vip,0) IN ({','.join('?' * len(levels))})"
        args += levels
    total = q1(f"SELECT COUNT(*) n FROM accounts WHERE {where}", args)["n"]
    in_stock = q1(f"SELECT COUNT(*) n FROM accounts WHERE {where} AND sold=0", args)["n"]
    pages = max(1, -(-total // PAGE_SIZE))
    page = min(max(page, 0), pages - 1)
    USER_FILTER[uid] = (game, rng, mask, page)
    rows = q(f"SELECT id,title,price,vip,sold FROM accounts WHERE {where} ORDER BY sold ASC, price ASC, id ASC LIMIT ? OFFSET ?",
             args + [PAGE_SIZE, page * PAGE_SIZE])

    kb = InlineKeyboardBuilder()
    for label, l, h in PRICE_PRESETS:
        on = (l, h) == (lo, hi)
        kb.button(text=("✅ " if on else "") + label, callback_data=f"f:{game}:{l}-{h}:{mask}:0")
    kb.button(text="✍️ Tự nhập giá", callback_data=f"fc:{game}:{mask}")
    kb.button(text=("✅ " if not mask else "") + "Mọi VIP", callback_data=f"f:{game}:{rng}:0:0")
    for v in VIP_LEVELS:
        on = mask >> v & 1
        kb.button(text=("✅ " if on else "") + f"VIP {v}", callback_data=f"f:{game}:{rng}:{mask ^ (1 << v)}:0")
    for r in rows:
        if r["sold"]:
            label = f"❌ ĐÃ BÁN #{r['id']} • VIP{r['vip'] or 0} • {r['title'][:16]}"
        else:
            label = f"🟢 #{r['id']} • VIP{r['vip'] or 0} • {r['title'][:16]} • {money(r['price'])}"
        kb.button(text=label, callback_data=f"acc:{r['id']}")
    nav = []
    if page > 0:
        nav.append(("◀️ Trước", f"f:{game}:{rng}:{mask}:{page - 1}"))
    if pages > 1:
        nav.append((f"📄 {page + 1}/{pages}", f"f:{game}:{rng}:{mask}:{page}"))
    if page < pages - 1:
        nav.append(("Sau ▶️", f"f:{game}:{rng}:{mask}:{page + 1}"))
    for t, cb in nav:
        kb.button(text=t, callback_data=cb)
    kb.button(text="🏠 Về Menu Chính", callback_data="menu:main")
    kb.adjust(3, 3, 1, 4, 3, *([1] * len(rows)), *([len(nav)] if nav else []), 1)

    text = (f"{GAMES.get(game, game)}\n"
            f"💵 Giá: <b>{price_text(lo, hi)}</b>\n"
            f"⭐ VIP: <b>{vip_text(mask)}</b> <i>(bấm nhiều VIP để chọn nhiều mức)</i>\n"
            f"📦 Tìm thấy: <b>{total}</b> acc (🟢 còn hàng: <b>{in_stock}</b>, ❌ đã bán: {total - in_stock}) • Trang {page + 1}/{pages}\n\n"
            + ("👇 Chọn acc để xem ảnh &amp; thông tin:" if rows else "😔 Không có acc phù hợp, hãy đổi bộ lọc."))
    if edit:
        try:
            await target.edit_text(text, reply_markup=kb.as_markup())
            return
        except TelegramBadRequest as e:
            if "not modified" in str(e):
                return
    await target.answer(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("game:"))
async def cb_game(c: CallbackQuery):
    game = c.data.split(":")[1]
    if game not in GAMES:
        return await c.answer()
    await show_filter(c.message, c.from_user.id, game, "0-0", 0)
    await c.answer()


@router.callback_query(F.data.startswith("f:"))
async def cb_filter(c: CallbackQuery):
    p = c.data.split(":")
    game, rng, mask = p[1], p[2], int(p[3])
    page = int(p[4]) if len(p) > 4 else 0
    await show_filter(c.message, c.from_user.id, game, rng, mask, page, edit=True)
    await c.answer()


@router.callback_query(F.data.startswith("fb:"))
async def cb_filter_back(c: CallbackQuery):
    game = c.data.split(":")[1]
    g, rng, mask, page = USER_FILTER.get(c.from_user.id, (game, "0-0", 0, 0))
    if g != game:
        rng, mask, page = "0-0", 0, 0
    await show_filter(c.message, c.from_user.id, game, rng, mask, page)
    await c.answer()


@router.callback_query(F.data.startswith("fc:"))
async def cb_filter_custom(c: CallbackQuery, state: FSMContext):
    _, game, mask = c.data.split(":")
    await state.set_state(PriceIn.rng)
    await state.update_data(game=game, mask=int(mask))
    await c.message.answer(
        "✍️ Nhập khoảng giá theo dạng <code>từ-đến</code>\n"
        "VD: <code>50000-200000</code> hoặc <code>50k-200k</code> hoặc <code>1tr-3tr</code>\n"
        "Chỉ muốn 'từ ... trở lên': <code>100k-</code>",
        reply_markup=nav_kb(f"fb:{game}", "⬅️ Quay lại danh sách"))
    await c.answer()


@router.message(PriceIn.rng)
async def filter_custom_input(m: Message, state: FSMContext):
    parts = re.split(r"\s*[-–~]\s*|\s+đến\s+", (m.text or "").strip().lower())
    try:
        lo = to_vnd(parts[0])
        hi = to_vnd(parts[1]) if len(parts) > 1 else 0
    except Exception:
        return await m.answer("❌ Sai định dạng. VD: <code>50k-200k</code>", reply_markup=back_main())
    lo, hi = min(lo, 10**9), min(hi, 10**9)
    if hi and hi < lo:
        lo, hi = hi, lo
    d = await state.get_data()
    await state.clear()
    await show_filter(m, m.from_user.id, d["game"], f"{lo}-{hi}", d["mask"])


@router.callback_query(F.data.startswith("acc:"))
async def cb_acc(c: CallbackQuery):
    aid = int(c.data.split(":")[1])
    a = q1("SELECT * FROM accounts WHERE id=?", (aid,))
    if not a:
        await c.answer("Acc không tồn tại!", show_alert=True)
        return
    status = "❌ <b>ĐÃ BÁN</b>" if a["sold"] else "🟢 <b>CÒN HÀNG</b>"
    head = (f"{GAMES.get(a['game'], a['game'])}\n"
            f"🆔 Mã acc: <b>#{a['id']}</b> • {status}\n"
            f"⭐ Cấp VIP: <b>VIP {a['vip'] or 0}</b>\n"
            f"📝 {esc((a['title'] or '')[:80])}\n"
            f"💵 Giá: <b>{money(a['price'])}</b>")
    info = f"ℹ️ <b>Mô tả acc #{a['id']}</b>\n{esc((a['info'] or '')[:1500])}"
    b = InlineKeyboardBuilder()
    if not a["sold"]:
        b.button(text=f"✅ MUA NGAY - {money(a['price'])}", callback_data=f"buy:{aid}")
    b.button(text="⬅️ Quay lại danh sách", callback_data=f"fb:{a['game']}")
    b.adjust(1)
    tail = "\n\n" + ("👇 Bạn có muốn mua acc này không?" if not a["sold"] else "😔 Acc này đã có người mua.")

    photos = json.loads(a["photos"] or "[]")
    sent = False
    if photos:
        try:
            media = [InputMediaPhoto(media=p) for p in photos[:10]]
            media[0] = InputMediaPhoto(media=photos[0], caption=head)
            await c.message.answer_media_group(media)
            # mô tả + nút mua chung 1 tin (có nút nên không bị tự xoá sau 60s)
            await c.message.answer(info + tail, reply_markup=b.as_markup())
            sent = True
        except Exception:
            logging.exception("Không gửi được ảnh acc #%s", aid)
    if not sent:
        await c.message.answer(head + "\n\n" + info + tail, reply_markup=b.as_markup())
    await c.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(c: CallbackQuery):
    aid = int(c.data.split(":")[1])
    uid = c.from_user.id
    ensure_user(c.from_user)
    a = q1("SELECT * FROM accounts WHERE id=?", (aid,))
    if not a or a["sold"]:
        await c.answer("Acc đã có người mua!", show_alert=True)
        return
    if balance(uid) < a["price"]:
        b = InlineKeyboardBuilder()
        b.button(text="💳 Nạp tiền", callback_data="menu:deposit")
        b.button(text="🏠 Menu Chính", callback_data="menu:main")
        b.adjust(1)
        await c.message.answer(
            f"❌ Số dư không đủ!\nCần: <b>{money(a['price'])}</b> | Có: <b>{money(balance(uid))}</b>\n"
            f"Còn thiếu: <b>{money(a['price'] - balance(uid))}</b>",
            reply_markup=b.as_markup())
        await c.answer()
        return
    cur = db.execute("UPDATE accounts SET sold=1,buyer=?,sold_at=? WHERE id=? AND sold=0",
                     (uid, int(time.time()), aid))
    if cur.rowcount == 0:
        await c.answer("Acc đã có người mua!", show_alert=True)
        return
    change_balance(uid, -a["price"], "buy", f"Mua acc #{aid} {a['title']}")
    await c.message.answer(
        f"🎉 <b>MUA THÀNH CÔNG ACC #{aid}</b>\n\n"
        f"🔐 Thông tin đăng nhập:\n<code>{esc(a['login'])}</code>\n\n"
        f"💰 Số dư còn: <b>{money(balance(uid))}</b>\n"
        f"⚠️ Vui lòng đổi mật khẩu &amp; liên kết ngay sau khi nhận.",
        reply_markup=back_main())
    uname = f"@{c.from_user.username}" if c.from_user.username else esc(c.from_user.full_name)
    for ad in ADMIN_IDS:
        try:
            await c.bot.send_message(
                ad, f"🛍 Khách <code>{uid}</code> ({uname}) vừa mua acc #{aid} - {money(a['price'])}")
        except Exception:
            pass
    await c.answer("Thành công!")


# ---- Nạp tiền (QR theo số tiền khách chọn) ----
class Dep(StatesGroup):
    amount = State()


def deposit_kb():
    b = InlineKeyboardBuilder()
    for v in (20000, 50000, 100000, 200000, 500000):
        b.button(text=money(v), callback_data=f"dep:{v}")
    b.button(text="✍️ Nhập số khác", callback_data="dep:custom")
    b.button(text="🏠 Menu Chính", callback_data="menu:main")
    b.adjust(3, 2, 1, 1)
    return b.as_markup()


def qr_caption(uid, amount=0):
    content = f"NAP{uid}"
    money_line = (f"💵 Số tiền: <b>{money(amount)}</b> (đã điền sẵn trong QR)" if amount
                  else "💵 Số tiền: <b>tuỳ bạn nhập trong app</b> (tối thiểu 10.000đ)")
    return (f"💳 <b>NẠP TIỀN TỰ ĐỘNG</b>\n\n"
            f"🏦 Ngân hàng: <b>MB Bank</b>\n"
            f"🔢 STK: <code>{BANK_ACCOUNT}</code>\n"
            f"👤 Chủ TK: <b>{BANK_OWNER}</b>\n"
            f"{money_line}\n"
            f"📝 Nội dung CK: <code>{content}</code>\n\n"
            f"⚠️ Giữ <b>đúng nội dung</b> để được cộng tiền tự động (1-2 phút).\n"
            f"👇 Muốn QR có sẵn số tiền khác, bấm chọn bên dưới.")


def _tlv(tag: str, val: str) -> str:
    return f"{tag}{len(val):02d}{val}"


def _crc16(data: str) -> int:
    crc = 0xFFFF
    for byte in data.encode():
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def vietqr_payload(amount: int, content: str) -> str:
    """Chuỗi VietQR chuẩn NAPAS 247 (có số tiền + nội dung chuyển khoản)."""
    acc = _tlv("00", BANK_BIN) + _tlv("01", BANK_ACCOUNT)
    merchant = _tlv("00", "A000000727") + _tlv("01", acc) + _tlv("02", "QRIBFTTA")
    p = _tlv("00", "01") + _tlv("01", "12" if amount else "11") + _tlv("38", merchant) + _tlv("53", "704")
    if amount:
        p += _tlv("54", str(int(amount)))
    p += _tlv("58", "VN") + _tlv("62", _tlv("08", content))
    p += "6304"
    return p + f"{_crc16(p):04X}"


def make_qr_png(amount: int, content: str) -> bytes:
    import segno
    buf = io.BytesIO()
    segno.make(vietqr_payload(amount, content), error="m", micro=False).save(
        buf, kind="png", scale=8, border=4, dark="black", light="white")
    return buf.getvalue()


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read()
    if not data.startswith(b"\x89PNG"):
        raise ValueError("vietqr.io không trả về ảnh PNG")
    return data


async def send_qr(target: Message, uid: int, amount: int = 0):
    cap = qr_caption(uid, amount)
    kb = deposit_kb()
    loop = asyncio.get_running_loop()
    content = f"NAP{uid}"
    # Cách 1: tự vẽ QR VietQR trên server (nhanh, không phụ thuộc web ngoài)
    try:
        data = await loop.run_in_executor(None, make_qr_png, amount, content)
        await target.answer_photo(BufferedInputFile(data, filename=f"qr_{amount}.png"), caption=cap, reply_markup=kb)
        return
    except Exception:
        logging.exception("Tự vẽ QR thất bại (đã cài segno chưa?), thử tải từ vietqr.io")
    # Cách 2: tải ảnh từ img.vietqr.io (có amount) rồi gửi lên
    try:
        url = (f"https://img.vietqr.io/image/{BANK_BIN}-{BANK_ACCOUNT}-compact2.png"
               f"?addInfo={quote(content)}&accountName={quote(BANK_OWNER)}")
        if amount:
            url += f"&amount={int(amount)}"
        data = await loop.run_in_executor(None, _download, url)
        await target.answer_photo(BufferedInputFile(data, filename=f"qr_{amount}.png"), caption=cap, reply_markup=kb)
        return
    except Exception:
        logging.exception("Tải QR từ vietqr.io thất bại")
    # Cách 3: gửi chữ
    await target.answer(cap + "\n\n(Không tạo được ảnh QR, hãy chuyển khoản thủ công theo thông tin trên.)",
                        reply_markup=kb)


@router.callback_query(F.data == "menu:deposit")
async def cb_deposit(c: CallbackQuery, state: FSMContext):
    await state.clear()
    ensure_user(c.from_user)
    await send_qr(c.message, c.from_user.id, 0)
    await c.answer()


@router.message(Command("nap"))
async def cmd_nap(m: Message, state: FSMContext):
    await state.clear()
    ensure_user(m.from_user)
    await send_qr(m, m.from_user.id, 0)


@router.callback_query(F.data.startswith("dep:"))
async def cb_dep(c: CallbackQuery, state: FSMContext):
    ensure_user(c.from_user)
    v = c.data.split(":")[1]
    if v == "custom":
        await state.set_state(Dep.amount)
        await c.message.answer(
            f"✍️ Nhập số tiền muốn nạp (tối thiểu {money(MIN_DEPOSIT)}).\nVD: <code>75000</code> hoặc <code>75k</code> hoặc <code>1tr</code>",
            reply_markup=nav_kb("menu:deposit", "⬅️ Quay lại Nạp tiền"))
    else:
        await state.clear()
        await send_qr(c.message, c.from_user.id, int(v))
    await c.answer()


@router.message(Dep.amount)
async def dep_amount(m: Message, state: FSMContext):
    try:
        amount = to_vnd(m.text or "")
    except Exception:
        amount = 0
    if amount < MIN_DEPOSIT or amount > MAX_DEPOSIT:
        await m.answer(f"❌ Số tiền không hợp lệ (từ {money(MIN_DEPOSIT)} đến {money(MAX_DEPOSIT)}).",
                       reply_markup=nav_kb("menu:deposit", "⬅️ Quay lại Nạp tiền"))
        return
    await state.clear()
    ensure_user(m.from_user)
    await send_qr(m, m.from_user.id, amount)


# ----------------------------- ADMIN -----------------------------
class EditAcc(StatesGroup):
    photos = State(); newid = State()


class AddAcc(StatesGroup):
    game = State(); price = State(); vip = State(); title = State(); info = State(); login = State(); photos = State()


class MoneyS(StatesGroup):
    data = State()


class BC(StatesGroup):
    text = State()


class PM(StatesGroup):
    uid = State(); text = State()


def admin_only(c: CallbackQuery):
    return is_admin(c.from_user.id)


@router.message(Command("admin"))
async def admin_cmd(m: Message):
    if is_admin(m.from_user.id):
        await m.answer("⚙️ <b>QUẢN LÝ HỆ THỐNG (ADMIN PANEL)</b>\n👇 Lựa chọn chức năng:", reply_markup=admin_menu())


@router.callback_query(F.data == "adm:home", admin_only)
async def adm_home(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer("⚙️ <b>QUẢN LÝ HỆ THỐNG (ADMIN PANEL)</b>\n👇 Lựa chọn chức năng:", reply_markup=admin_menu())
    await c.answer()


@router.callback_query(F.data == "adm:users", admin_only)
async def adm_users(c: CallbackQuery):
    rows = q("SELECT * FROM users ORDER BY balance DESC LIMIT 40")
    total = q1("SELECT COUNT(*) n, COALESCE(SUM(balance),0) s FROM users")
    lines = [f"<code>{r['id']}</code> | @{esc(r['username'] or '-')} | {money(r['balance'])}" for r in rows]
    await c.message.answer(
        f"👥 <b>KHÁCH HÀNG</b>: {total['n']} | Tổng số dư: {money(total['s'])}\n(Top 40)\n\n" + "\n".join(lines),
        reply_markup=admin_menu())
    await c.answer()


@router.callback_query(F.data == "adm:stats", admin_only)
async def adm_stats(c: CallbackQuery):
    dep = q1("SELECT COALESCE(SUM(amount),0) s FROM tx WHERE type='deposit'")["s"]
    sold = q1("SELECT COUNT(*) n, COALESCE(SUM(price),0) s FROM accounts WHERE sold=1 AND COALESCE(buyer,0)>0")
    stock = q1("SELECT COUNT(*) n FROM accounts WHERE sold=0")["n"]
    today = int(time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d")))
    td = q1("SELECT COALESCE(SUM(price),0) s, COUNT(*) n FROM accounts WHERE sold=1 AND COALESCE(buyer,0)>0 AND sold_at>=?", (today,))
    await c.message.answer(
        f"📊 <b>THỐNG KÊ</b>\n💳 Tổng tiền khách đã nạp: {money(dep)}\n"
        f"🛍 Đã bán: {sold['n']} acc = {money(sold['s'])}\n"
        f"📅 Hôm nay: {td['n']} acc = {money(td['s'])}\n📦 Còn trong kho: {stock} acc",
        reply_markup=admin_menu())
    await c.answer()


ADMIN_GUIDE = (
    "📖 <b>HƯỚNG DẪN ADMIN</b>\n\n"
    "<b>➕ Thêm acc</b>: Admin Panel → Thêm Acc Mới → chọn game → nhập giá → chọn VIP → "
    "tiêu đề → mô tả → <code>user|pass</code> → gửi ảnh (tối đa 10) → gõ /done.\n\n"
    "<b>📦 Quản lý acc</b>: Admin Panel → Quản Lý / Xoá Acc (hoặc gõ <code>/xem MÃ</code>). Bấm vào acc để:\n"
    "• 🖼 Thêm ảnh • 🔄 Thay toàn bộ ảnh • 👁 Xem ảnh\n"
    "• 🔢 Đổi mã số acc • 🔁 Đổi trạng thái (còn hàng ↔ đã bán) • 🗑 Xoá acc (xoá được cả acc đã bán)\n\n"
    "<b>💰 Cộng/trừ tiền</b>: bấm nút Cộng/Trừ Tiền rồi nhập <code>ID SỐ_TIỀN</code> "
    "(trừ thì để số âm). Hoặc gõ nhanh:\n"
    "• <code>/cong ID SỐ_TIỀN</code> • <code>/tru ID SỐ_TIỀN</code>\n\n"
    "<b>👥 Khách hàng</b>: xem top 40 khách theo số dư.\n"
    "<b>📊 Thống kê</b>: tổng tiền nạp, số acc đã bán, doanh thu hôm nay, tồn kho.\n"
    "<b>📢 Broadcast</b>: gửi thông báo cho TẤT CẢ khách. <b>👤 Gửi tin riêng</b>: gửi cho 1 ID.\n\n"
    "<b>💳 Nạp tiền tự động</b>: khách chuyển khoản đúng nội dung <code>NAP+ID</code> → "
    "SePay gọi webhook → bot tự cộng tiền và báo cho khách + admin.\n"
    "Nạp sai nội dung: tự cộng thủ công bằng <code>/cong ID SỐ_TIỀN</code> sau khi kiểm tra bill.\n\n"
    "<b>💾 Sao lưu</b>: bot TỰ sao lưu database vào chat này (tin được ghim <code>💾 AUTO_BACKUP</code>, "
    "<b>đừng xoá / bỏ ghim</b>) và TỰ khôi phục khi khởi động lại. "
    "Gõ <code>/backup</code> để nhận thêm 1 bản lưu thủ công về máy.\n\n"
    "<b>🧹 Tự xoá tin</b>: tin rác của bot tự xoá sau 1 phút; bấm tác vụ khác thì tin cũ biến mất.\n\n"
    "<b>Lệnh hữu ích</b>: /menu menu chính • /admin mở panel • /huy huỷ thao tác • /done kết thúc gửi ảnh."
)


@router.message(Command("backup"))
async def cmd_backup(m: Message):
    if not is_admin(m.from_user.id):
        return
    tmp = "backup_tmp.db"
    dst = sqlite3.connect(tmp)
    try:
        db.backup(dst)
    finally:
        dst.close()
    try:
        await m.answer_document(FSInputFile(tmp, filename=f"shop_backup_{time.strftime('%Y%m%d_%H%M')}.db"),
                                caption="💾 File sao lưu database. Hãy cất giữ cẩn thận (có tài khoản acc &amp; số dư khách).")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


@router.callback_query(F.data == "adm:guide", admin_only)
async def adm_guide(c: CallbackQuery):
    await c.message.answer(ADMIN_GUIDE, reply_markup=admin_menu())
    await c.answer()


# ---- cộng/trừ tiền ----
@router.callback_query(F.data == "adm:money", admin_only)
async def adm_money(c: CallbackQuery, state: FSMContext):
    await state.set_state(MoneyS.data)
    await c.message.answer("💰 Nhập: <code>ID_TELE SỐ_TIỀN</code>\nVD cộng: <code>123456789 50000</code>\nVD trừ: <code>123456789 -20000</code>", reply_markup=nav_kb())
    await c.answer()


async def do_money(bot: Bot, admin_id, uid, amount):
    change_balance(uid, amount, "admin", f"Admin {'cộng' if amount > 0 else 'trừ'} tiền")
    try:
        await bot.send_message(uid, f"💰 Admin đã {'cộng' if amount > 0 else 'trừ'} <b>{money(abs(amount))}</b> vào tài khoản.\nSố dư: <b>{money(balance(uid))}</b>")
    except Exception:
        pass
    return f"✅ Đã {'cộng' if amount > 0 else 'trừ'} {money(abs(amount))} cho <code>{uid}</code>. Số dư mới: {money(balance(uid))}"


@router.message(MoneyS.data)
async def adm_money_data(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    parts = (m.text or "").split()
    try:
        uid, amount = int(parts[0]), int(parts[1])
    except Exception:
        await m.answer("❌ Sai cú pháp. VD: <code>123456789 50000</code>", reply_markup=nav_kb())
        return
    await state.clear()
    await m.answer(await do_money(m.bot, m.from_user.id, uid, amount), reply_markup=admin_menu())


@router.message(Command("cong"))
async def cmd_cong(m: Message):
    if is_admin(m.from_user.id):
        try:
            _, uid, amt = m.text.split()
            await m.answer(await do_money(m.bot, m.from_user.id, int(uid), abs(int(amt))))
        except Exception:
            await m.answer("Cú pháp: /cong ID SỐ_TIỀN")


@router.message(Command("tru"))
async def cmd_tru(m: Message):
    if is_admin(m.from_user.id):
        try:
            _, uid, amt = m.text.split()
            await m.answer(await do_money(m.bot, m.from_user.id, int(uid), -abs(int(amt))))
        except Exception:
            await m.answer("Cú pháp: /tru ID SỐ_TIỀN")


# ---- thêm acc ----
@router.callback_query(F.data == "adm:add", admin_only)
async def adm_add(c: CallbackQuery, state: FSMContext):
    b = InlineKeyboardBuilder()
    for k, n in GAMES.items():
        b.button(text=n, callback_data=f"addgame:{k}")
    b.button(text="⬅️ Quay lại Admin", callback_data="adm:home")
    b.button(text="🏠 Menu Chính", callback_data="menu:main")
    b.adjust(1)
    await state.set_state(AddAcc.game)
    await c.message.answer("➕ Chọn game cho acc mới:", reply_markup=b.as_markup())
    await c.answer()


@router.callback_query(F.data.startswith("addgame:"), admin_only)
async def adm_add_game(c: CallbackQuery, state: FSMContext):
    await state.update_data(game=c.data.split(":")[1], photos=[])
    await state.set_state(AddAcc.price)
    await c.message.answer("💵 Nhập giá bán (số, VD: 150000 hoặc 150k):", reply_markup=nav_kb())
    await c.answer()


@router.message(AddAcc.price)
async def add_price(m: Message, state: FSMContext):
    try:
        v = to_vnd(m.text or "")
    except Exception:
        v = 0
    if not v or v > 10**9:
        return await m.answer("❌ Nhập số tiền hợp lệ (VD: 150000).", reply_markup=nav_kb())
    await state.update_data(price=v)
    await state.set_state(AddAcc.vip)
    kb = InlineKeyboardBuilder()
    for lv in VIP_LEVELS:
        kb.button(text=f"VIP {lv}", callback_data=f"addvip:{lv}")
    kb.button(text="⬅️ Quay lại Admin", callback_data="adm:home")
    kb.button(text="🏠 Menu Chính", callback_data="menu:main")
    kb.adjust(*([3] * (len(VIP_LEVELS) // 3)), *([len(VIP_LEVELS) % 3] if len(VIP_LEVELS) % 3 else []), 2)
    await m.answer("⭐ Chọn cấp VIP cho acc:", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("addvip:"), admin_only)
async def add_vip(c: CallbackQuery, state: FSMContext):
    await state.update_data(vip=int(c.data.split(":")[1]))
    await state.set_state(AddAcc.title)
    await c.message.answer("📝 Nhập tiêu đề ngắn (VD: Acc rank Cao Thủ 50 skin):", reply_markup=nav_kb())
    await c.answer()


@router.message(AddAcc.title)
async def add_title(m: Message, state: FSMContext):
    if not (m.text or "").strip():
        return await m.answer("❌ Hãy nhập bằng chữ (không gửi ảnh/file).", reply_markup=nav_kb())
    await state.update_data(title=m.text.strip()[:120])
    await state.set_state(AddAcc.info)
    await m.answer("ℹ️ Nhập mô tả chi tiết (rank, skin, tướng, súng, level...):", reply_markup=nav_kb())


@router.message(AddAcc.info)
async def add_info(m: Message, state: FSMContext):
    if not (m.text or "").strip():
        return await m.answer("❌ Hãy nhập bằng chữ (không gửi ảnh/file).", reply_markup=nav_kb())
    await state.update_data(info=m.text.strip()[:1500])
    await state.set_state(AddAcc.login)
    await m.answer("🔐 Nhập thông tin đăng nhập (VD: <code>user|pass</code>) - chỉ gửi cho khách SAU KHI mua:", reply_markup=nav_kb())


@router.message(AddAcc.login)
async def add_login(m: Message, state: FSMContext):
    if not (m.text or "").strip():
        return await m.answer("❌ Hãy nhập bằng chữ, ví dụ: <code>user|pass</code>", reply_markup=nav_kb())
    await state.update_data(login=m.text.strip())
    await state.set_state(AddAcc.photos)
    await m.answer("🖼 Gửi các ảnh của acc (tối đa 10). Xong gõ /done (không có ảnh cũng gõ /done).", reply_markup=nav_kb())


@router.message(AddAcc.photos, F.photo)
async def add_photo(m: Message, state: FSMContext):
    d = await state.get_data()
    photos = d.get("photos", [])
    if len(photos) < 10:
        photos.append(m.photo[-1].file_id)
    await state.update_data(photos=photos)
    await m.answer(f"✅ Đã nhận {len(photos)} ảnh. Gửi thêm hoặc /done.", reply_markup=nav_kb())


@router.message(AddAcc.photos, Command("done"))
async def add_done(m: Message, state: FSMContext):
    d = await state.get_data()
    await state.clear()
    cur = db.execute(
        "INSERT INTO accounts(game,title,price,vip,info,login,photos,created) VALUES(?,?,?,?,?,?,?,?)",
        (d["game"], d["title"], d["price"], d.get("vip", 0), d["info"], d["login"], json.dumps(d["photos"]), int(time.time())))
    await m.answer(f"✅ Đã thêm acc <b>#{cur.lastrowid}</b> - VIP {d.get('vip', 0)} - {money(d['price'])}", reply_markup=admin_menu())


# ---- quản lý acc ----
ADM_PAGE = 10


async def render_adm_list(target: Message, page: int, edit: bool):
    total = q1("SELECT COUNT(*) n FROM accounts")["n"]
    stock = q1("SELECT COUNT(*) n FROM accounts WHERE sold=0")["n"]
    pages = max(1, -(-total // ADM_PAGE))
    page = min(max(page, 0), pages - 1)
    rows = q("SELECT id,game,title,price,vip,sold FROM accounts ORDER BY id DESC LIMIT ? OFFSET ?",
             (ADM_PAGE, page * ADM_PAGE))
    kb = InlineKeyboardBuilder()
    for r in rows:
        mark = "❌" if r["sold"] else "🟢"
        kb.button(text=f"{mark} #{r['id']} {GAMES.get(r['game'], '')[:2]} V{r['vip'] or 0} {r['title'][:16]} {money(r['price'])}",
                  callback_data=f"am:{r['id']}:{page}")
    nav = []
    if page > 0:
        nav.append(("◀️ Trước", f"adm:list:{page - 1}"))
    nav.append((f"📄 {page + 1}/{pages}", f"adm:list:{page}"))
    if page < pages - 1:
        nav.append(("Sau ▶️", f"adm:list:{page + 1}"))
    for t, cb in nav:
        kb.button(text=t, callback_data=cb)
    kb.button(text="⬅️ Admin", callback_data="adm:home")
    kb.adjust(*([1] * len(rows)), len(nav), 1)
    text = (f"📦 <b>KHO ACC</b>: {total} acc (🟢 còn {stock} • ❌ đã bán {total - stock})\n"
            f"Bấm vào acc để sửa ảnh / đổi mã / xoá.\nXem nhanh 1 acc: <code>/xem MÃ</code>")
    if edit:
        try:
            await target.edit_text(text, reply_markup=kb.as_markup())
            return
        except TelegramBadRequest as e:
            if "not modified" in str(e):
                return
    await target.answer(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("adm:list"), admin_only)
async def adm_list(c: CallbackQuery):
    p = c.data.split(":")
    await render_adm_list(c.message, int(p[2]) if len(p) > 2 else 0, edit=len(p) > 2)
    await c.answer()


@router.callback_query(F.data.startswith("del:"), admin_only)
async def adm_del(c: CallbackQuery):
    _, aid, page = c.data.split(":")
    a = q1("SELECT sold,buyer FROM accounts WHERE id=?", (int(aid),))
    if not a:
        return await c.answer("Acc không tồn tại!", show_alert=True)
    warn = ""
    if a["sold"] and a["buyer"]:
        warn = f"\n\n⚠️ Acc này ĐÃ BÁN cho <code>{a['buyer']}</code>. Xoá xong khách đó sẽ <b>không xem lại được</b> tài khoản/mật khẩu trong Lịch Sử."
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Xác nhận XOÁ", callback_data=f"delc:{aid}:{page}")
    kb.button(text="❌ Huỷ", callback_data=f"am:{aid}:{page}")
    kb.adjust(2)
    await c.message.edit_text(f"⚠️ Xoá acc <b>#{aid}</b>? Không thể khôi phục.{warn}", reply_markup=kb.as_markup())
    await c.answer()


@router.callback_query(F.data.startswith("delc:"), admin_only)
async def adm_del_confirm(c: CallbackQuery):
    _, aid, page = c.data.split(":")
    db.execute("DELETE FROM accounts WHERE id=?", (int(aid),))
    await c.answer("Đã xoá!")
    await render_adm_list(c.message, int(page), edit=True)


# ---- đổi trạng thái acc (còn hàng <-> đã bán) ----
@router.callback_query(F.data.startswith("st:"), admin_only)
async def adm_status(c: CallbackQuery):
    _, aid, page = c.data.split(":")
    a = q1("SELECT sold,buyer FROM accounts WHERE id=?", (int(aid),))
    if not a:
        return await c.answer("Acc không tồn tại!", show_alert=True)
    kb = InlineKeyboardBuilder()
    if a["sold"]:
        warn = ""
        if a["buyer"]:
            warn = f"\n⚠️ Acc đang thuộc khách <code>{a['buyer']}</code>, khách đó sẽ không xem lại được acc trong Lịch Sử nữa (tiền KHÔNG tự hoàn, nếu cần dùng /cong)."
        text = f"🔁 Chuyển acc <b>#{aid}</b> từ ❌ ĐÃ BÁN sang 🟢 <b>CÒN HÀNG</b>?{warn}"
    else:
        text = f"🔁 Chuyển acc <b>#{aid}</b> từ 🟢 CÒN HÀNG sang ❌ <b>ĐÃ BÁN</b> (ẩn khỏi kho, không tính doanh thu)?"
    kb.button(text="✅ Xác nhận", callback_data=f"stc:{aid}:{page}")
    kb.button(text="❌ Huỷ", callback_data=f"am:{aid}:{page}")
    kb.adjust(2)
    await c.message.edit_text(text, reply_markup=kb.as_markup())
    await c.answer()


@router.callback_query(F.data.startswith("stc:"), admin_only)
async def adm_status_confirm(c: CallbackQuery):
    _, aid, page = c.data.split(":")
    a = q1("SELECT sold FROM accounts WHERE id=?", (int(aid),))
    if not a:
        return await c.answer("Acc không tồn tại!", show_alert=True)
    if a["sold"]:
        db.execute("UPDATE accounts SET sold=0,buyer=NULL,sold_at=NULL WHERE id=?", (int(aid),))
        await c.answer("Đã chuyển sang CÒN HÀNG")
    else:
        db.execute("UPDATE accounts SET sold=1,buyer=0,sold_at=? WHERE id=?", (int(time.time()), int(aid)))
        await c.answer("Đã chuyển sang ĐÃ BÁN")
    await render_acc_manage(c.message, int(aid), int(page), edit=True)


async def render_acc_manage(target: Message, aid: int, page: int, edit: bool):
    a = q1("SELECT * FROM accounts WHERE id=?", (aid,))
    if not a:
        return await target.answer("❌ Không tìm thấy acc.")
    n_photo = len(json.loads(a["photos"] or "[]"))
    kb = InlineKeyboardBuilder()
    kb.button(text=f"🖼 Thêm ảnh (hiện {n_photo}/10)", callback_data=f"pa:{aid}")
    kb.button(text="🔄 Thay toàn bộ ảnh", callback_data=f"pr:{aid}")
    kb.button(text="👁 Xem ảnh hiện tại", callback_data=f"pv:{aid}")
    kb.button(text="🔢 Đổi mã số acc", callback_data=f"pi:{aid}")
    kb.button(text=("🔁 Đổi trạng thái → CÒN HÀNG" if a["sold"] else "🔁 Đổi trạng thái → ĐÃ BÁN"),
              callback_data=f"st:{aid}:{page}")
    kb.button(text="🗑 Xoá acc", callback_data=f"del:{aid}:{page}")
    kb.button(text="⬅️ Danh sách", callback_data=f"adm:list:{page}")
    kb.adjust(1, 1, 1, 1, 1, 2)
    text = (f"🆔 <b>#{aid}</b> | {GAMES.get(a['game'], a['game'])} | VIP {a['vip'] or 0}\n"
            f"📝 {esc(a['title'])}\n💵 {money(a['price'])}\nℹ️ {esc(a['info'])}\n"
            f"🔐 <code>{esc(a['login'])}</code>\n🖼 Số ảnh: {n_photo}\n"
            f"📌 {(('❌ ĐÃ BÁN cho ID ' + str(a['buyer'])) if a['buyer'] else '❌ ĐÃ BÁN (admin đánh dấu)') if a['sold'] else '🟢 Còn hàng'}")
    if edit:
        try:
            await target.edit_text(text, reply_markup=kb.as_markup())
            return
        except TelegramBadRequest as e:
            if "not modified" in str(e):
                return
    await target.answer(text, reply_markup=kb.as_markup())


@router.message(Command("xem"))
async def cmd_xem(m: Message):
    if not is_admin(m.from_user.id):
        return
    try:
        aid = int(m.text.split()[1])
    except Exception:
        return await m.answer("Cú pháp: /xem MÃ_ACC")
    await render_acc_manage(m, aid, 0, edit=False)


@router.callback_query(F.data.startswith("am:"), admin_only)
async def adm_acc_manage(c: CallbackQuery, state: FSMContext):
    await state.clear()
    _, aid, page = c.data.split(":")
    await render_acc_manage(c.message, int(aid), int(page), edit=True)
    await c.answer()


@router.callback_query(F.data.startswith("pv:"), admin_only)
async def adm_view_photos(c: CallbackQuery):
    a = q1("SELECT photos FROM accounts WHERE id=?", (int(c.data.split(":")[1]),))
    photos = json.loads(a["photos"] or "[]") if a else []
    if not photos:
        return await c.answer("Acc này chưa có ảnh.", show_alert=True)
    await c.message.answer_media_group([InputMediaPhoto(media=p) for p in photos[:10]])
    await c.answer()


# ---- thêm ảnh / thay toàn bộ ảnh ----
@router.callback_query(F.data.regexp(r"^p[ar]:\d+$"), admin_only)
async def photo_edit_start(c: CallbackQuery, state: FSMContext):
    mode, aid = c.data.split(":")
    a = q1("SELECT photos FROM accounts WHERE id=?", (int(aid),))
    if not a:
        return await c.answer("Không tìm thấy acc.", show_alert=True)
    base = json.loads(a["photos"] or "[]") if mode == "pa" else []
    await state.set_state(EditAcc.photos)
    await state.update_data(aid=int(aid), photos=base, mode=mode)
    if mode == "pa":
        tip = f"🖼 Acc #{aid} đang có {len(base)} ảnh. Gửi thêm ảnh mới (tối đa 10 ảnh tổng)."
    else:
        tip = f"🔄 Thay toàn bộ ảnh acc #{aid}: ảnh cũ sẽ bị xoá, gửi bộ ảnh MỚI (tối đa 10)."
    await c.message.answer(tip + "\nXong gõ /done • Huỷ gõ /huy\n<i>(Gõ /done ngay mà chưa gửi ảnh ở chế độ thay = xoá hết ảnh)</i>",
                           reply_markup=nav_kb(f"am:{aid}:0", "⬅️ Quay lại acc"))
    await c.answer()


@router.message(EditAcc.photos, F.photo)
async def photo_edit_recv(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    d = await state.get_data()
    photos = d.get("photos", [])
    if len(photos) >= 10:
        return await m.answer("⚠️ Đã đủ 10 ảnh, gõ /done để lưu.", reply_markup=nav_kb(f"am:{d['aid']}:0", "⬅️ Quay lại acc"))
    photos.append(m.photo[-1].file_id)
    await state.update_data(photos=photos)
    await m.answer(f"✅ Tổng {len(photos)} ảnh. Gửi thêm hoặc /done.", reply_markup=nav_kb(f"am:{d['aid']}:0", "⬅️ Quay lại acc"))


@router.message(EditAcc.photos, Command("done"))
async def photo_edit_done(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    d = await state.get_data()
    await state.clear()
    db.execute("UPDATE accounts SET photos=? WHERE id=?", (json.dumps(d["photos"]), d["aid"]))
    await m.answer(f"✅ Đã lưu {len(d['photos'])} ảnh cho acc #{d['aid']}.")
    await render_acc_manage(m, d["aid"], 0, edit=False)


# ---- đổi mã số acc ----
@router.callback_query(F.data.startswith("pi:"), admin_only)
async def id_edit_start(c: CallbackQuery, state: FSMContext):
    aid = int(c.data.split(":")[1])
    await state.set_state(EditAcc.newid)
    await state.update_data(aid=aid)
    await c.message.answer(f"🔢 Nhập <b>mã số mới</b> cho acc #{aid} (số nguyên dương, chưa có acc nào dùng).\nHuỷ gõ /huy",
                           reply_markup=nav_kb("adm:list", "⬅️ Danh sách"))
    await c.answer()


@router.message(EditAcc.newid)
async def id_edit_done(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    txt = (m.text or "").strip().lstrip("#")
    if not txt.isdigit() or int(txt) <= 0:
        return await m.answer("❌ Mã phải là số nguyên dương. Nhập lại hoặc /huy.", reply_markup=nav_kb("adm:list", "⬅️ Danh sách"))
    d = await state.get_data()
    old, new = d["aid"], int(txt)
    if new != old and q1("SELECT id FROM accounts WHERE id=?", (new,)):
        return await m.answer(f"❌ Mã #{new} đã có acc khác dùng. Nhập mã khác hoặc /huy.", reply_markup=nav_kb("adm:list", "⬅️ Danh sách"))
    await state.clear()
    if new != old:
        db.execute("UPDATE accounts SET id=? WHERE id=?", (new, old))
    await m.answer(f"✅ Đã đổi mã acc #{old} → <b>#{new}</b>.")
    await render_acc_manage(m, new, 0, edit=False)


# ---- broadcast ----
@router.callback_query(F.data == "adm:bc", admin_only)
async def adm_bc(c: CallbackQuery, state: FSMContext):
    await state.set_state(BC.text)
    await c.message.answer("📢 Nhập nội dung thông báo gửi TOÀN BỘ khách:", reply_markup=nav_kb())
    await c.answer()


@router.message(BC.text)
async def bc_send(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    ok = fail = 0
    for r in q("SELECT id FROM users"):
        try:
            await m.bot.send_message(r["id"], f"📢 <b>THÔNG BÁO</b>\n\n{esc(m.text)}")
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await m.answer(f"✅ Gửi xong: {ok} thành công, {fail} lỗi.", reply_markup=admin_menu())


# ---- gửi riêng ----
@router.callback_query(F.data == "adm:pm", admin_only)
async def adm_pm(c: CallbackQuery, state: FSMContext):
    await state.set_state(PM.uid)
    await c.message.answer("👤 Nhập ID Telegram của khách:", reply_markup=nav_kb())
    await c.answer()


@router.message(PM.uid)
async def pm_uid(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    if not (m.text or "").strip().isdigit():
        return await m.answer("❌ ID phải là số.", reply_markup=nav_kb())
    await state.update_data(uid=int(m.text))
    await state.set_state(PM.text)
    await m.answer("✍️ Nhập nội dung tin nhắn:", reply_markup=nav_kb())


@router.message(PM.text)
async def pm_text(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    d = await state.get_data()
    await state.clear()
    try:
        await m.bot.send_message(d["uid"], f"💬 <b>Tin nhắn từ Admin</b>\n\n{esc(m.text)}")
        await m.answer("✅ Đã gửi.", reply_markup=admin_menu())
    except Exception as e:
        await m.answer(f"❌ Lỗi: {esc(e)}", reply_markup=admin_menu())


# ----------------------------- TỰ SAO LƯU DATABASE VÀO TELEGRAM -----------------------------
BACKUP_INTERVAL = 30
BACKUP_STATE = {"changes": None, "msg_id": None}


async def do_auto_backup():
    if not ADMIN_IDS:
        return
    target = min(ADMIN_IDS)
    changes = db.total_changes
    tmp = "autobackup_tmp.db"
    dst = sqlite3.connect(tmp)
    try:
        db.backup(dst)
    finally:
        dst.close()
    try:
        msg = await BOT.send_document(
            target, FSInputFile(tmp, filename="shop_autobackup.db"),
            caption="💾 AUTO_BACKUP " + time.strftime("%d/%m %H:%M:%S"), disable_notification=True)
        await BOT.pin_chat_message(target, msg.message_id, disable_notification=True)
        old = BACKUP_STATE["msg_id"]
        if old:
            try:
                await BOT.delete_message(target, old)
            except Exception:
                pass
        BACKUP_STATE.update(changes=changes, msg_id=msg.message_id)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


async def auto_backup_loop():
    BACKUP_STATE["changes"] = db.total_changes
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        try:
            if db.total_changes != BACKUP_STATE["changes"]:
                await do_auto_backup()
        except Exception:
            logging.exception("Tự sao lưu lỗi")


async def final_backup():
    try:
        if BACKUP_STATE["changes"] is not None and db.total_changes != BACKUP_STATE["changes"]:
            await do_auto_backup()
            logging.info("Đã sao lưu lần cuối trước khi tắt")
    except Exception:
        logging.exception("Sao lưu lần cuối lỗi")


# ----------------------------- FLASK (web server cho Render + webhook SePay) -----------------------------
flask_app = Flask(__name__)
MAIN_LOOP = None
BOT = None


@flask_app.route("/")
def home():
    return "Shop bot is running", 200


@flask_app.route("/health")
def health():
    return "ok", 200


async def process_deposit(data: dict):
    """Chạy trong event loop của bot để DB luôn được truy cập từ 1 luồng."""
    if str(data.get("transferType", "")).lower() != "in":
        return
    acc = str(data.get("accountNumber") or "")
    if acc and acc != BANK_ACCOUNT:
        logging.warning("Bỏ qua giao dịch của STK khác: %s", acc)
        return
    text = f"{data.get('content', '')} {data.get('code', '')} {data.get('description', '')}".upper()
    m = re.search(r"NAP\s*(\d{5,15})", text)
    if not m:
        logging.info("Giao dịch không có nội dung NAP<ID>: %r", data.get("content"))
        return
    uid = int(m.group(1))
    try:
        amount = int(float(data.get("transferAmount", 0)))
    except (TypeError, ValueError):
        return
    ref_id = data.get("id") or data.get("referenceCode") or f"{data.get('transactionDate')}|{amount}|{text}"
    ref = f"sepay:{ref_id}"
    if amount > 0 and change_balance(uid, amount, "deposit", "Nạp tiền MB Bank", ref):
        logging.info("Đã cộng %s cho %s", amount, uid)
        try:
            await BOT.send_message(uid, f"✅ <b>NẠP TIỀN THÀNH CÔNG</b>\n+{money(amount)}\n💰 Số dư: <b>{money(balance(uid))}</b>",
                                   reply_markup=back_main())
        except Exception:
            pass
        for ad in ADMIN_IDS:
            try:
                await BOT.send_message(ad, f"💳 Khách <code>{uid}</code> vừa nạp {money(amount)}")
            except Exception:
                pass


@flask_app.route("/sepay", methods=["POST"])
def sepay_hook():
    """SePay gọi vào đây khi có biến động số dư: https://<tên-app>.onrender.com/sepay"""
    if not SEPAY_API_KEY:
        logging.error("Chưa đặt SEPAY_API_KEY nên từ chối webhook (tránh bị giả mạo nạp tiền)")
        return jsonify(success=False, error="server chua cau hinh SEPAY_API_KEY"), 503
    if not hmac.compare_digest(request.headers.get("Authorization", ""), f"Apikey {SEPAY_API_KEY}"):
        return jsonify(success=False), 401
    data = request.get_json(force=True, silent=True) or {}
    logging.info("Webhook SePay: %s", {k: data.get(k) for k in ("id", "transferType", "transferAmount", "content")})
    try:
        asyncio.run_coroutine_threadsafe(process_deposit(data), MAIN_LOOP).result(timeout=20)
    except Exception:
        logging.exception("Lỗi xử lý nạp tiền")
        return jsonify(success=False), 500
    return jsonify(success=True)


def run_flask():
    serve(flask_app, host="0.0.0.0", port=WEBHOOK_PORT)


async def main():
    global MAIN_LOOP, BOT
    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        raise SystemExit("LỖI: chưa có BOT_TOKEN hợp lệ. Vào Render > Environment điền BOT_TOKEN (lấy ở @BotFather).")
    if not ADMIN_IDS:
        logging.warning("ADMIN_IDS đang trống -> không ai vào được /admin và không thể tự sao lưu.")
    if not SEPAY_API_KEY:
        logging.warning("SEPAY_API_KEY đang trống -> webhook nạp tiền tự động sẽ bị từ chối.")
    MAIN_LOOP = asyncio.get_running_loop()
    BOT = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    BOT.session.middleware(TrackMW())
    dp = Dispatcher()
    dp.include_router(router)
    if AUTO_BACKUP and RESTORE_STATUS != "error":
        dp.shutdown.register(final_backup)

    threading.Thread(target=run_flask, daemon=True).start()
    if RESTORE_STATUS == "error":
        for ad in ADMIN_IDS:
            try:
                await BOT.send_message(
                    ad, "⚠️ <b>CẢNH BÁO</b>: không khôi phục được database từ bản sao lưu Telegram. "
                        "Bot chạy với database RỖNG và <b>TẠM DỪNG tự sao lưu</b> để không ghi đè bản cũ. "
                        "Hãy deploy lại (restart) để thử khôi phục lần nữa.")
            except Exception:
                pass
    elif AUTO_BACKUP:
        asyncio.create_task(auto_backup_loop())
        notice = {"restored": "💾 ✅ Đã <b>tự khôi phục</b> database từ bản sao lưu trên Telegram.",
                  "none": "ℹ️ Chưa có bản sao lưu nào, đang dùng database mới."}.get(RESTORE_STATUS, "")
        if DB_TEMP:
            notice = ("⚠️ <b>CẢNH BÁO</b>: chưa gắn Disk nên bot dùng database tạm, nhưng đã bật "
                      "<b>tự sao lưu vào Telegram</b> (file ghim trong chat này, đừng xoá/bỏ ghim).\n" + notice)
        if notice:
            for ad in ADMIN_IDS:
                try:
                    await BOT.send_message(ad, notice)
                except Exception:
                    pass
    await BOT.delete_webhook(drop_pending_updates=False)
    logging.info("Bot + Flask đang chạy... (tự sao lưu: %s, khôi phục: %s)", AUTO_BACKUP, RESTORE_STATUS)
    await dp.start_polling(BOT)


if __name__ == "__main__":
    asyncio.run(main())
