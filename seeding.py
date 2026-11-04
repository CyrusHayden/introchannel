"""
Seeding bot - Crypto Trading Halls
Tai khoan Telegram phu (Telethon) dang recap ket qua trade vao cac nhom/channel
ma TK phu da tham gia (tu quet), chia 3 khung gio. Chay tren GitHub Actions (repo public).
Repo public -> log khong in ten nhom/noi dung; moi chi tiet gui rieng ve tai khoan chinh.

Luong:
  1. Doc tin moi nhat tu tai khoan chinh (MAIN_ACCOUNT) gui sang tai khoan phu.
     Co ket qua moi (win/loss/PnL) -> dung; khong co -> dung ket qua cu trong state.json.
  2. Tu quet tat ca nhom/channel TK phu da tham gia, chia khung theo ID nhom % 3.
  3. Moi nhom 1 mau (khong trung trong cung khung, khong trung mau hom truoc cua nhom do).
  4. Nhom thuong -> gui tin; channel co nhom binh luan -> reply vao bai moi nhat.
  5. Gian cach ngau nhien giua cac lan gui; bao cao ve tai khoan chinh.
"""
import asyncio
import json
import os
import random
import re
import sys
from datetime import datetime, timezone, timedelta

from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Channel, Chat

BASE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE, "state.json")
TEMPLATES_FILE = os.path.join(BASE, "templates.txt")

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION = os.environ["TG_SESSION"]
MAIN_ACCOUNT = os.environ["MAIN_ACCOUNT"]          # username tai khoan chinh, vd: @hayden
CHANNEL_LINK = os.environ["CHANNEL_LINK"]               # secret, khong ghi trong code
SKIP_WORDS = ["hall"]   # bo qua nhom/channel co chu nay trong ten (kenh cua minh)
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
DELAY_MIN = int(os.environ.get("DELAY_MIN", "90"))   # giay
DELAY_MAX = int(os.environ.get("DELAY_MAX", "240"))

VN = timezone(timedelta(hours=7))
SLOT_NAMES = {0: "21:30 (phien My)", 1: "08:30 (phien A)", 2: "15:00 (phien London)"}


def detect_slot():
    forced = os.environ.get("SLOT", "").strip()
    if forced in ("0", "1", "2"):
        return int(forced)
    h = datetime.now(VN).hour
    if 20 <= h or h < 2:
        return 0
    if 2 <= h < 12:
        return 1
    return 2


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"result": None, "last_msg_id": 0, "last_template": {}}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_templates():
    with open(TEMPLATES_FILE, encoding="utf-8") as f:
        parts = [p.strip() for p in f.read().split("\n---\n")]
    return [p for p in parts if p and not p.startswith("#")]


async def scan_targets(client):
    """Quet tat ca nhom/channel tai khoan phu dang tham gia.
    Nhom -> gui tin. Channel -> reply vao bai moi nhat qua nhom binh luan.
    Bo qua: chat rieng; ten co chu trong SKIP_WORDS ("HALL" = kenh cua minh);
    TK phu la admin/chu; nhom cam gui tin; channel khong co nhom binh luan;
    nhom binh luan cua channel da co trong danh sach (tranh dang 2 lan)."""
    def blocked(rights):
        return bool(rights and rights.send_messages)

    out, linked = [], set()
    async for d in client.iter_dialogs():
        e = d.entity
        name = d.name or ""
        if any(w in name.lower() for w in SKIP_WORDS):
            continue
        if isinstance(e, Chat):
            if getattr(e, "deactivated", False) or blocked(e.default_banned_rights):
                continue
            out.append((e.id, name, e))
        elif isinstance(e, Channel):
            if e.creator or e.admin_rights:
                continue
            if e.broadcast:
                try:
                    full = await client(GetFullChannelRequest(e))
                except Exception:  # noqa
                    continue
                lid = full.full_chat.linked_chat_id
                if not lid:
                    continue  # channel khong cho binh luan
                linked.add(lid)
                out.append((e.id, name, e))
            elif e.megagroup:
                if blocked(e.default_banned_rights) or blocked(e.banned_rights):
                    continue
                out.append((e.id, name, e))
    return [t for t in out if t[0] not in linked]


def parse_result(text):
    """Nhan dang: '2/3 +386%' / '5 win 1 loss +23.5%' / 'win 5 loss 1 pnl 23.5%' / 'W5 L1 +23.5%'."""
    t = text.lower().replace(",", ".")

    def num(patterns):
        for p in patterns:
            m = re.search(p, t)
            if m:
                return m.group(1)
        return None

    frac = re.search(r"(\d+)\s*/\s*(\d+)", t)   # kieu "2/3 +386%"
    # "win 5 loss 1" (chu truoc so) hay "5 win 1 loss" (so truoc chu)?
    first_digit = re.search(r"\d", t)
    first_kw = re.search(r"win|\bw\s*\d", t)
    kw_first = bool(first_kw and first_digit and first_kw.start() < first_digit.start())
    if kw_first:
        win = num([r"win\w*\s*[:=]?\s*(\d+)", r"\bw\s*(\d+)"])
        loss = num([r"loss\w*\s*[:=]?\s*(\d+)", r"\bl\s*(\d+)"]) or "0"
    else:
        win = num([r"(\d+)\s*win"])
        loss = num([r"(\d+)\s*loss"]) or "0"
    pnl = num([r"pnl\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)", r"([+-]?\d+(?:\.\d+)?)\s*%"])
    if frac and int(frac.group(2)) >= int(frac.group(1)):
        win, loss = frac.group(1), str(int(frac.group(2)) - int(frac.group(1)))
    if win is None or pnl is None:
        return None
    w, l = int(win), int(loss)
    p = float(pnl)
    total = w + l
    return {
        "win": w,
        "loss": l,
        "total": total,
        "winrate": round(w * 100 / total) if total else 0,
        "pnl": f"{'+' if p >= 0 else ''}{p:g}",
    }


def pick_templates(groups, templates, last_template):
    """Moi nhom 1 mau: uu tien khong trung trong khung, khong trung mau lan truoc cua nhom."""
    n = len(templates)
    used = {}
    result = {}
    for g in groups:
        avoid = last_template.get(g)
        candidates = [i for i in range(n) if i != avoid]
        least = min(used.get(i, 0) for i in candidates)
        pool = [i for i in candidates if used.get(i, 0) == least]
        i = random.choice(pool)
        used[i] = used.get(i, 0) + 1
        result[g] = i
    return result


async def fetch_new_result(client, state):
    main = await client.get_entity(MAIN_ACCOUNT)
    async for msg in client.iter_messages(main, limit=20):
        if msg.out or not msg.text:
            continue
        if msg.id <= state.get("last_msg_id", 0):
            break
        parsed = parse_result(msg.text)
        if parsed:
            state["result"] = parsed
            state["last_msg_id"] = msg.id
            state["result_date"] = msg.date.astimezone(VN).strftime("%Y-%m-%d %H:%M")
            return main, True
        # tin moi nhung khong doc duoc -> bao lai, van dung ket qua cu
        await client.send_message(main, "⚠️ Seeding bot: không đọc được kết quả trong tin này. "
                                        "Mẫu đúng: `2/3 +386%`. Tạm dùng kết quả cũ.")
        state["last_msg_id"] = msg.id
        break
    return main, False


async def send_to_target(client, entity, text):
    if isinstance(entity, Channel) and entity.broadcast:
        # channel: reply (comment) vao bai moi nhat
        posts = await client.get_messages(entity, limit=1)
        if not posts:
            raise RuntimeError("channel chua co bai")
        await client.send_message(entity, text, comment_to=posts[0].id, link_preview=False)
        return "comment"
    await client.send_message(entity, text, link_preview=False)
    return "msg"


async def main():
    slot = detect_slot()
    state = load_state()
    templates = load_templates()

    client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
    await client.start()
    main_ent, is_new = await fetch_new_result(client, state)
    targets = await scan_targets(client)
    # chia khung theo ID nhom (co dinh: vao nhom moi khong lam xao tron nhom cu)
    chosen = [t for t in targets if t[0] % 3 == slot]
    by_key = {str(t[0]): t for t in chosen}
    groups = list(by_key.keys())
    print(f"Khung {slot} - {len(groups)}/{len(targets)} nhom - dry_run={DRY_RUN}")
    res = state.get("result")
    if not res:
        await client.send_message(main_ent, "⚠️ Seeding bot: chưa có kết quả nào. "
                                            "Nhắn mẫu `2/3 +386%` cho tài khoản này.")
        save_state(state)
        return

    picks = pick_templates(groups, templates, state.get("last_template", {}))
    random.shuffle(groups)
    report, previews = [], []
    for idx, key in enumerate(groups):
        _, name, entity = by_key[key]
        g = name
        text = templates[picks[key]].format(link=CHANNEL_LINK, **res)
        try:
            if DRY_RUN:
                kind = "dry"
                previews.append(f"▫️ {g} (mẫu {picks[key] + 1}):\n{text}")
            else:
                kind = await send_to_target(client, entity, text)
            state.setdefault("last_template", {})[key] = picks[key]
            report.append(f"✅ {g} ({kind}, mẫu {picks[key] + 1})")
        except errors.FloodWaitError as e:
            report.append(f"⏳ {g}: FloodWait {e.seconds}s - dừng khung này")
            if e.seconds > 300:
                break
            await asyncio.sleep(e.seconds + 5)
        except errors.SlowModeWaitError as e:
            report.append(f"🐢 {g}: slow mode {e.seconds}s - bỏ qua")
        except (errors.ChatWriteForbiddenError, errors.ChatRestrictedError,
                errors.UserBannedInChannelError, errors.ChannelPrivateError) as e:
            report.append(f"🚫 {g}: không có quyền gửi ({type(e).__name__})")
        except errors.PeerFloodError:
            report.append(f"🛑 {g}: PEER_FLOOD - Telegram nghi spam, dừng hẳn")
            break
        except Exception as e:  # noqa
            report.append(f"❌ {g}: {type(e).__name__}: {e}")
        save_state(state)
        if idx < len(groups) - 1 and not DRY_RUN:
            await asyncio.sleep(random.randint(DELAY_MIN, DELAY_MAX))

    head = (f"📤 Seeding {SLOT_NAMES[slot]}{' [DRY RUN]' if DRY_RUN else ''}\n"
            f"Kết quả dùng: {res['win']}W/{res['loss']}L, PnL {res['pnl']}% "
            f"({'mới' if is_new else 'cũ, ' + state.get('result_date', '')})\n")
    await client.send_message(main_ent, head + "\n".join(report or ["(không có nhóm trong khung này)"]))
    if previews:  # chay thu: gui ban xem truoc tung tin ve tai khoan chinh
        chunk = ""
        for p in previews:
            if len(chunk) + len(p) > 3500:
                await client.send_message(main_ent, chunk, link_preview=False)
                chunk = ""
            chunk += p + "\n\n"
        if chunk:
            await client.send_message(main_ent, chunk, link_preview=False)
    ok = sum(1 for r in report if r.startswith("✅"))
    print(f"Xong: {ok}/{len(groups)} thanh cong")
    save_state(state)
    await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:  # noqa - chi in loai loi, khong in chi tiet (log public)
        print(f"LOI: {type(e).__name__}")
        sys.exit(1)
