# HƯỚNG DẪN CÀI BOT SHOP LÊN RENDER

## 1. Các file cần có (up lên GitHub)

| File | Bắt buộc | Công dụng |
|---|---|---|
| `bot.py` | ✅ | Toàn bộ code bot + web Flask |
| `requirements.txt` | ✅ | Danh sách thư viện (aiogram, flask, waitress) |
| `.python-version` | nên có | Ép Render dùng Python 3.12 |
| `.gitignore` | nên có | Không up `shop.db` và file bí mật lên GitHub |
| `.env.example` | không | File mẫu để nhớ các key (không dùng khi chạy) |

> ❌ KHÔNG up lên GitHub: `shop.db`, file `.env` thật, token bot.

## 2. Các KEY (Environment Variables) cần điền trên Render

| Key | Bắt buộc | Giá trị | Lấy ở đâu |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | Token bot, dạng `123456789:AAxxxx` | Chat @BotFather → `/newbot` |
| `ADMIN_IDS` | ✅ | ID Telegram của admin. Nhiều admin ngăn bằng dấu phẩy: `111,222` | Chat @userinfobot |
| `SEPAY_API_KEY` | ✅ | Chuỗi bí mật bạn **tự đặt** (VD 30 ký tự ngẫu nhiên). Phải **giống hệt** khóa nhập ở SePay | Tự đặt |
| `SUPPORT` | nên có | Username hỗ trợ, VD `@shop_support` | Tự điền |
| `DB_FILE` | ✅ nếu có Disk | `/data/shop.db` | Xem mục 4 |
| `PYTHON_VERSION` | không | `3.12.3` (nếu không có file `.python-version`) | |
| `PORT` | ❌ không điền | Render tự cấp | |

Thông tin ngân hàng (MB, STK 3030777777, tên NGUYEN TIEN DAT) nằm sẵn trong đầu file `bot.py`
(`BANK_CODE`, `BANK_ACCOUNT`, `BANK_OWNER`). Muốn đổi thì sửa ở đó.

## 3. Tạo Web Service trên Render

1. Up các file ở mục 1 lên 1 repo GitHub (để Private).
2. Vào render.com → **New +** → **Web Service** → nối repo đó.
3. Điền:
   - **Runtime / Language**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Health Check Path** (mục Advanced): `/health`
4. Mục **Environment** → thêm các key ở mục 2.
5. Bấm **Create Web Service**, chờ deploy xong. Xem tab **Logs**, thấy dòng `Bot + Flask đang chạy...` là OK.
6. Link web của bạn dạng `https://ten-app.onrender.com`. Mở link thấy chữ `Shop bot is running` là server sống.
7. Vào Telegram chat với bot, gõ `/start`, rồi `/admin` để thử.

## 4. Giữ dữ liệu không bị mất (RẤT QUAN TRỌNG)

Render **không lưu file lâu dài** nếu không gắn Disk. Mỗi lần deploy lại / restart, `shop.db`
(acc, ảnh, số dư khách) sẽ **mất sạch**.

Cách làm (cần gói trả phí, VD Starter):
1. Trong Web Service → mục **Disks** → **Add Disk**.
2. **Mount Path**: `/data` — dung lượng 1 GB là dư.
3. Thêm key `DB_FILE` = `/data/shop.db` rồi deploy lại.

Gói **free** không có Disk và còn tự ngủ sau ~15 phút không có truy cập
(lúc ngủ bot không trả lời khách). Chạy shop thật nên dùng gói trả phí.

## 5. Cài nạp tiền tự động bằng SePay

1. Đăng ký sepay.vn, **liên kết tài khoản MB Bank 3030777777** vào SePay.
2. Vào mục **Tích hợp Webhooks** → thêm webhook mới:
   - **URL**: `https://ten-app.onrender.com/sepay`
   - **Sự kiện**: có tiền vào
   - **Kiểu chứng thực**: `API Key`, giá trị = đúng `SEPAY_API_KEY` bạn đặt ở Render
3. Test: dùng tài khoản khác chuyển 10.000đ với nội dung `NAP<ID Telegram của bạn>`.
   Sau 1-2 phút bot nhắn "NẠP TIỀN THÀNH CÔNG".

(Tên các mục trong SePay có thể thay đổi theo thời gian, cứ tìm mục Webhook trong phần tích hợp.)

## 6. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Bot không trả lời | Xem tab Logs; kiểm tra `BOT_TOKEN` đúng chưa; gói free có thể đang ngủ |
| Gõ `/admin` không ra | `ADMIN_IDS` sai. Lấy lại ID ở @userinfobot (chỉ gồm số) |
| Nạp tiền không được cộng | Khách ghi sai nội dung (phải `NAP` + ID); `SEPAY_API_KEY` không khớp; URL webhook sai. Xem lịch sử gọi webhook trong SePay |
| Báo lỗi `Conflict: terminated by other getUpdates` | Đang có 2 bản bot chạy cùng token (VD chạy trên máy cá nhân). Tắt bản còn lại |
| Mất hết acc sau khi deploy | Chưa gắn Disk (mục 4) |
| Lộ token | @BotFather → `/revoke` để tạo token mới, rồi cập nhật lại `BOT_TOKEN` |

## 7. Sao lưu

Định kỳ tải file `shop.db` về máy bằng cách gõ `/backup` trong chat với bot (chỉ admin dùng được) để phòng khi sự cố.
