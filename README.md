# introchannel – Seeding bot

Tài khoản Telegram phụ tự đăng kết quả trade hằng ngày vào mọi nhóm/channel nó đã tham gia.

- **Lịch (giờ VN):** 21:30 (phiên Mỹ) · 08:30 (phiên Á) · 15:00 (phiên London). Mỗi nhóm nhận 1 tin/ngày, chia khung theo ID nhóm.
- **Nhập kết quả:** từ tài khoản chính nhắn cho tài khoản phụ, ví dụ `2/3 +386%`. Không nhắn thì bot dùng kết quả cũ.
- **Bỏ qua:** chat riêng, tên có chữ "HALL", nhóm cấm nhắn, channel không có bình luận, nơi TK phụ là admin.
- **Mẫu tin:** `templates.txt` (10 mẫu, xoay vòng, không trùng trong khung và với lần trước của nhóm).

## Secrets (Settings → Secrets and variables → Actions)
| Tên | Công dụng |
|---|---|
| TG_API_ID | API ID của TK phụ (my.telegram.org) |
| TG_API_HASH | API HASH của TK phụ |
| TG_SESSION | Chuỗi đăng nhập TK phụ, tạo bằng `python gen_session.py` trên laptop |
| MAIN_ACCOUNT | Username tài khoản chính (người gửi kết quả),  |
| CHANNEL_LINK | Link channel dùng trong mẫu tin (chữ HERE/JOIN) |

## Chạy thử
Actions → Seeding → Run workflow → `dry_run = true` (không gửi thật, bản xem trước gửi về tài khoản chính).

## Bảo mật (repo public)
- Mọi thông tin cá nhân (tài khoản, link channel, session) chỉ nằm trong Secrets.
- Log Actions chỉ in số lượng nhóm, không in tên nhóm/nội dung.
- `state.json` lưu trong cache của Actions, không commit vào repo.
