"""
Chay 1 LAN tren laptop de tao TG_SESSION cho tai khoan phu.
  pip install telethon
  python gen_session.py
Nhap API ID, API HASH (my.telegram.org), so dien thoai TK phu, ma Telegram gui ve.
Chuoi session duoc luu vao file tg_session.txt va tu mo bang Notepad.
-> Ctrl+A, Ctrl+C trong Notepad -> dan vao GitHub Secret TG_SESSION -> XOA file tg_session.txt.
KHONG chup man hinh / gui chuoi nay cho ai: ai co no la dang nhap duoc tai khoan.
"""
import os
import subprocess
import sys

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("API ID: ").strip())
api_hash = input("API HASH: ").strip()
with TelegramClient(StringSession(), api_id, api_hash) as client:
    session = client.session.save()

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_session.txt")
with open(path, "w", encoding="utf-8") as f:
    f.write(session)
print(f"\nDa luu session vao: {path}")
print("Copy noi dung file -> GitHub Secret TG_SESSION, roi XOA file nay.")
if sys.platform.startswith("win"):
    subprocess.Popen(["notepad.exe", path])
