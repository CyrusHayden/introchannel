"""
Chay 1 LAN tren laptop de tao TG_SESSION cho tai khoan phu.
  pip install telethon
  python gen_session.py
Nhap API ID, API HASH (lay o my.telegram.org), so dien thoai TK phu, ma Telegram gui ve.
Copy chuoi in ra -> GitHub repo > Settings > Secrets > TG_SESSION.
KHONG chia se chuoi nay cho ai: ai co no la dang nhap duoc tai khoan.
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("API ID: ").strip())
api_hash = input("API HASH: ").strip()
with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\n=== TG_SESSION (copy toan bo dong duoi) ===\n")
    print(client.session.save())
