import os, json, time, random, threading, requests, telebot
from telebot import types
from datetime import datetime

BOT_TOKEN  = os.getenv("BOT_TOKEN", "8906411015:AAF7K9jBEFEqHk--i0-rKDHPfoEGkUhGPPk")
OWNER_ID   = 8133158656
DB_FILE    = "db.json"
BOT_VERS   = "v1.0 PREMIUM"
DEVELOPER  = "@abhi09hub"
BOT_NAME   = "TELEGRAM OSINT"

FORCE_CHANNELS = [
    ("BACKUP CHANNEL", "@abhihub09"),
    ("OFFICIAL GROUP",  "@NexoraField"),
]
CHANNEL_URLS = {
    "@abhihub09":   "https://t.me/abhihub09",
    "@NexoraField": "https://t.me/NexoraField",
}

CREDITS_PER_LOOKUP  = 3
STARTING_CREDITS    = 10
REFERRER_BONUS      = 5
REFEREE_BONUS       = 2
SPIN_COOLDOWN_HOURS = 24
MAX_DAILY_SPINS     = 3

API_TIMEOUT_SEC = 60
RETRY_ATTEMPTS  = 3
RETRY_WAIT_SEC  = 2

API_URL_NUMBER = "https://abhi-numberinfoapi.vercel.app/api/number/ABHI-LIFE-2026"

AUTO_DELETE_GROUP_MINUTES = 5

CONTACT_DEV     = "@abhi09hub"
CONTACT_CHANNEL = "@abhihub09"
CONTACT_GROUP   = "@NexoraField"

PRICING = [
    ("12 Hour Trial",  "₹25"),
    ("24 Hour Pass",   "₹40"),
    ("48 Hour Pass",   "₹70"),
    ("5 Day Pass",     "₹150"),
    ("10 Day Pass",    "₹250"),
    ("20 Day Pass",    "₹450"),
    ("30 Day Pass",    "₹600"),
    ("Lifetime",       "₹1500"),
]

DIVIDER  = "━" * 24
SEP      = "║"
THIN_SEP = "│"

def premium_footer() -> str:
    return f"\n\n<code>NEXORA OSINT  •  {BOT_VERS}</code>"

def credit_bar(credits: int, length: int = 12) -> str:
    filled = min(credits, length)
    return "█" * filled + "░" * (length - filled)

def box(emoji: str, title: str, body: str) -> str:
    lines = [
        f"╔{'═' * 26}╗",
        f"{SEP}  {emoji}  <b>{title}</b>",
        f"{SEP}  <code>{DIVIDER}</code>",
    ]
    for ln in (body or "").split("\n"):
        lines.append(f"{SEP}  {ln}")
    lines.append(f"╚{'═' * 26}╝")
    return "\n".join(lines)

def slim_box(emoji: str, title: str, body: str) -> str:
    lines = [
        f"╭─〔 {emoji} <b>{title}</b> 〕",
        f"{THIN_SEP}  {'─' * 20}",
    ]
    for ln in (body or "").split("\n"):
        lines.append(f"{THIN_SEP}  {ln}")
    lines.append(f"╰{'─' * 26}╯")
    return "\n".join(lines)

def loading_text(label: str, frame: int = 0) -> str:
    spinners = ["◐", "◓", "◑", "◒"]
    return f"<code>{spinners[frame % 4]}  {label}...</code>"

db_lock = threading.Lock()
db: dict = {
    "users":     {},
    "banned":    {},
    "bot_state": {"enabled": True},
    "codes":     {},
    "stats":     {"total_lookups": 0, "total_spins": 0},
}

def load_db():
    global db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            pass

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def ensure_user(uid: int):
    uid_s = str(uid)
    with db_lock:
        if uid_s not in db["users"]:
            db["users"][uid_s] = {
                "credits":          STARTING_CREDITS,
                "premium":          False,
                "referrer":         None,
                "referrals":        0,
                "last_spin_at":     None,
                "daily_spin_count": 0,
                "lookups":          0,
                "joined_at":        int(time.time()),
                "username":         None,
                "first_name":       None,
            }
            save_db()

def get_user(uid: int) -> dict:
    ensure_user(uid)
    return db["users"][str(uid)]

def update_user_meta(uid: int, first_name: str, username: str):
    ensure_user(uid)
    with db_lock:
        db["users"][str(uid)]["first_name"] = first_name
        db["users"][str(uid)]["username"]   = username

def is_banned(uid: int) -> bool:
    return str(uid) in db.get("banned", {})

def add_credits(uid: int, amount: int):
    ensure_user(uid)
    with db_lock:
        db["users"][str(uid)]["credits"] += int(amount)
        save_db()

def set_premium(uid: int, val: bool):
    ensure_user(uid)
    with db_lock:
        db["users"][str(uid)]["premium"] = bool(val)
        save_db()

def set_bot_enabled(val: bool):
    with db_lock:
        db["bot_state"]["enabled"] = bool(val)
        save_db()

def is_bot_enabled() -> bool:
    return db.get("bot_state", {}).get("enabled", True)

def create_code(code: str, credits: int = 0, premium: bool = False, uses: int = 1):
    code = code.strip().upper()
    with db_lock:
        db["codes"][code] = {
            "credits":    int(credits),
            "premium":    bool(premium),
            "uses_left":  int(uses),
            "created_at": int(time.time()),
        }
        save_db()

def redeem_code(uid: int, code: str):
    code = code.strip().upper()
    with db_lock:
        c = db["codes"].get(code)
        if not c:
            return False, "❌ Invalid code."
        if c["uses_left"] <= 0:
            return False, "⏰ Code expired."
        ensure_user(uid)
        u = db["users"][str(uid)]
        gained = []
        if c.get("credits", 0) > 0:
            u["credits"] += int(c["credits"])
            gained.append(f"+{c['credits']} Credits")
        if c.get("premium", False):
            u["premium"] = True
            gained.append("Premium Activated")
        c["uses_left"] -= 1
        save_db()
        return True, " • ".join(gained) if gained else "✅ Redeemed."

def global_stat_bump(key: str):
    with db_lock:
        db.setdefault("stats", {})[key] = db["stats"].get(key, 0) + 1
        save_db()

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

def _safe_delete(chat_id: int, msg_id: int):
    try:
        bot.delete_message(chat_id, msg_id)
    except Exception:
        pass

def schedule_delete(chat_id: int, msg_id: int):
    if chat_id is None or chat_id >= 0:
        return
    t = threading.Timer(
        AUTO_DELETE_GROUP_MINUTES * 60, _safe_delete, args=(chat_id, msg_id)
    )
    t.daemon = True
    t.start()

def bot_send(chat_id: int, text: str, **kwargs):
    m = bot.send_message(chat_id, text, **kwargs)
    schedule_delete(chat_id, m.message_id)
    return m

def bot_reply(message, text: str, **kwargs):
    m = bot.reply_to(message, text, **kwargs)
    schedule_delete(message.chat.id, m.message_id)
    return m

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True, row_width=2)
    kb.row("TG LOOKUP",      "NUMBER INFO")
    kb.row("VEHICLE INFO",   "AADHAR INFO")
    kb.row("MY CREDITS",     "DAILY SPIN")
    kb.row("PROFILE",        "HELP")
    kb.row("PURCHASE API",   "CONTACT DEV")
    return kb

def build_join_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    for name, handle in FORCE_CHANNELS:
        url = CHANNEL_URLS.get(handle, handle.replace("@", "https://t.me/"))
        kb.add(types.InlineKeyboardButton(
            text=f"➕  {name}  —  JOIN NOW",
            url=url
        ))
    kb.add(types.InlineKeyboardButton(
        text="✅  VERIFY KARO  —  CHECK KAREIN",
        callback_data="refresh_check"
    ))
    return kb

def contact_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("Developer DM", url="https://t.me/abhi09hub"))
    kb.add(types.InlineKeyboardButton("Official Group", url="https://t.me/NexoraField"))
    kb.add(types.InlineKeyboardButton("Channel", url="https://t.me/abhihub09"))
    return kb

def coming_soon_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(
        "Developer se baat karo",
        url="https://t.me/abhi09hub"
    ))
    kb.add(types.InlineKeyboardButton(
        "Channel join karo (updates ke liye)",
        url="https://t.me/abhihub09"
    ))
    return kb

def purchase_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(
        "Number Info API kharido",
        callback_data="purchase_numberinfo"
    ))
    kb.add(types.InlineKeyboardButton(
        "Developer se contact karo",
        url="https://t.me/abhi09hub"
    ))
    kb.add(types.InlineKeyboardButton(
        "Channel join karo",
        url="https://t.me/abhihub09"
    ))
    return kb

def owner_panel_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        ("Bot ON / OFF",          "owner_toggle"),
        ("Add / Remove Credits",  "owner_addcredits"),
        ("Toggle Premium",        "owner_premium"),
        ("Check User",            "owner_checkuser"),
        ("Ban / Unban",           "owner_ban"),
        ("Create Code",           "owner_createcode"),
        ("Broadcast",             "owner_broadcast"),
        ("Ban List",              "owner_banlist"),
        ("Bot Stats",             "owner_stats"),
    ]
    for label, cb in buttons:
        kb.add(types.InlineKeyboardButton(label, callback_data=cb))
    return kb

def try_react(chat_id: int, msg_id: int, emoji: str):
    try:
        bot.set_message_reaction(
            chat_id, msg_id,
            reaction=[types.ReactionTypeEmoji(emoji=emoji)]
        )
        return
    except Exception:
        pass
    try:
        bot.set_message_reaction(chat_id, msg_id, emoji)
    except Exception:
        pass

def extract_handle(url_or_handle: str) -> str:
    s = url_or_handle.strip()
    if s.startswith("@"):
        return s
    if "t.me/" in s:
        part = s.split("t.me/")[1].strip().strip("/").split("/")[0]
        return "@" + part if not part.startswith("+") else s
    return "@" + s

def user_in_channel(handle: str, uid: int) -> bool:
    try:
        member = bot.get_chat_member(handle, uid)
        return member.status in ("creator", "administrator", "member", "restricted")
    except Exception as e:
        print(f"[CHANNEL CHECK] {handle} uid={uid} -> {e}")
        return False

def all_force_joined(uid: int) -> bool:
    for _, handle in FORCE_CHANNELS:
        if not user_in_channel(extract_handle(handle), uid):
            return False
    return True

def require_join(message):
    text = (
        "╔══════════════════════════╗\n"
        f"{SEP}   <b>ACCESS LOCKED</b>   \n"
        f"{SEP}  <code>{'─' * 24}</code>\n"
        f"{SEP}\n"
        f"{SEP}  Dono channels join karo\n"
        f"{SEP}  aur niche verify karo.\n"
        f"{SEP}\n"
        f"{SEP}  Step 1: Channels join karo\n"
        f"{SEP}  Step 2: Verify dabao\n"
        f"{SEP}\n"
        "╚══════════════════════════╝\n"
        f"{premium_footer()}"
    )
    bot_send(message.chat.id, text, reply_markup=build_join_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "refresh_check")
def cb_refresh_check(call):
    uid = call.from_user.id
    if is_banned(uid):
        bot.answer_callback_query(call.id, "You are banned.", show_alert=True)
        return
    if all_force_joined(uid):
        bot.answer_callback_query(call.id, "Verified! Welcome!", show_alert=False)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_welcome(call.message.chat.id, uid, call.from_user.first_name)
    else:
        bot.answer_callback_query(
            call.id,
            "Abhi bhi join nahi kiya - pehle dono channels join karo!",
            show_alert=True,
        )

def send_welcome(chat_id: int, uid: int, first_name: str = ""):
    u        = get_user(uid)
    name     = first_name or u.get("first_name") or "User"
    cr       = u["credits"]
    bar      = credit_bar(cr)
    prem     = "<b>PREMIUM</b>" if u["premium"] else "Free"
    ref_link = f"https://t.me/{bot.get_me().username}?start={uid}"

    caption = (
        "╔══════════════════════════╗\n"
        f"{SEP}  <b>NEXORA OSINT BOT</b>  \n"
        f"{SEP}  <code>{'═' * 24}</code>\n"
        f"{SEP}\n"
        f"{SEP}  Welcome, <b>{name}</b>!\n"
        f"{SEP}  {prem}\n"
        f"{SEP}\n"
        f"{SEP}  Credits: [{bar}] <b>{cr}</b>\n"
        f"{SEP}\n"
        f"{SEP}  <code>{'─' * 24}</code>\n"
        f"{SEP}  /num     ->  Number Info\n"
        f"{SEP}  <code>{'─' * 24}</code>\n"
        f"{SEP}  /spin    ->  Daily Spin\n"
        f"{SEP}  /refer   ->  Earn Credits\n"
        f"{SEP}  /profile ->  Your Stats\n"
        f"{SEP}  /help    ->  All Commands\n"
        f"{SEP}\n"
        "╚══════════════════════════╝\n\n"
        f"Referral Link:\n"
        f"<code>{ref_link}</code>\n"
        f"{premium_footer()}"
    )
    bot_send(chat_id, caption, reply_markup=main_keyboard())

def _http_get_json(url: str, params: dict) -> dict:
    r = requests.get(url, params=params, timeout=API_TIMEOUT_SEC)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {"raw": r.text}

def api_number_lookup(number: str) -> dict:
    return _http_get_json(API_URL_NUMBER, {"number": number})

def _fmt_val(v) -> str:
    if v is None:
        return "<i>N/A</i>"
    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    return str(v)

def _fmt_record(rec) -> str:
    if isinstance(rec, dict):
        lines = []
        for k, v in rec.items():
            key = str(k).replace("_", " ").title()
            lines.append(f"<b>{key}:</b>  {_fmt_val(v)}")
        return "\n".join(lines)
    return _fmt_val(rec)

def fmt_records(data) -> str:
    if data is None:
        return "<i>No data returned.</i>"
    if isinstance(data, dict):
        for k in ("data", "results", "records", "result", "response"):
            if k in data and isinstance(data[k], (list, dict)):
                return _fmt_record(data[k])
        return _fmt_record(data)
    return _fmt_val(data)

def lookup_cost_and_consume(uid: int) -> bool:
    u = get_user(uid)
    if u["premium"]:
        return True
    if u["credits"] < CREDITS_PER_LOOKUP:
        return False
    add_credits(uid, -CREDITS_PER_LOOKUP)
    return True

def should_suppress(message) -> bool:
    if message.content_type != "text":
        return False
    txt = (message.text or "").strip()
    if not txt or txt.startswith("/"):
        return False
    if txt.startswith("@"):
        return True
    if len("".join(c for c in txt if c.isdigit())) >= 8:
        return True
    return False

def gate(message) -> bool:
    if not is_bot_enabled():
        bot_reply(message, "Bot abhi offline hai. Baad mein try karo.")
        return False
    if is_banned(message.from_user.id):
        bot_reply(message, "Aap banned hain is bot se.")
        return False
    if not all_force_joined(message.from_user.id):
        require_join(message)
        return False
    return True

def owner_gate(message) -> bool:
    return message.from_user.id == OWNER_ID

def _animate_search(chat_id: int, msg_id: int, label: str, stop_evt: threading.Event):
    frame = 0
    while not stop_evt.is_set():
        try:
            bot.edit_message_text(loading_text(label, frame), chat_id, msg_id)
        except Exception:
            pass
        frame += 1
        time.sleep(0.45)

def send_coming_soon(message, feature: str):
    body = (
        f"<b>{feature}</b> feature abhi add hone wala hai.\n\n"
        f"<i>Kuch hi time me available hoga.</i>\n\n"
        f"<code>{'─' * 22}</code>\n"
        f"<b>Contact:</b>\n"
        f"Dev:     {CONTACT_DEV}\n"
        f"Channel: {CONTACT_CHANNEL}\n"
        f"Group:   {CONTACT_GROUP}"
    )
    txt = box("🚧", "COMING SOON", body) + premium_footer()
    bot_send(message.chat.id, txt, reply_markup=coming_soon_kb())

def send_purchase_menu(message):
    body = (
        f"Yaha se aap API kharid sakte hain.\n\n"
        f"<b>Available APIs:</b>\n"
        f"1. Number Info API\n\n"
        f"<i>Baaki APIs (TG, Vehicle, Aadhar) coming soon.</i>\n\n"
        f"<code>{'─' * 22}</code>\n"
        f"Kis API ki pricing dekhni hai? Niche choose karo."
    )
    txt = box("🛒", "PURCHASE API", body) + premium_footer()
    bot_send(message.chat.id, txt, reply_markup=purchase_kb())

@bot.callback_query_handler(func=lambda c: c.data == "purchase_numberinfo")
def cb_purchase_numberinfo(call):
    bot.answer_callback_query(call.id)
    price_lines = []
    for plan, price in PRICING:
        price_lines.append(f"{SEP}  {plan:<16}  <b>{price}</b>")
    body = "\n".join(price_lines)
    text = (
        "╔══════════════════════════╗\n"
        f"{SEP}  <b>NUMBER INFO API</b>\n"
        f"{SEP}  <code>{'═' * 24}</code>\n"
        f"{SEP}  <b>PRICING:</b>\n"
        f"{SEP}  <code>{'─' * 24}</code>\n"
        f"{body}\n"
        f"{SEP}  <code>{'─' * 24}</code>\n"
        f"{SEP}  <b>Features:</b>\n"
        f"{SEP}  Name + Address\n"
        f"{SEP}  Circle + Alt Number\n"
        f"{SEP}  Email (if available)\n"
        f"{SEP}  <code>{'─' * 24}</code>\n"
        f"{SEP}  <b>Purchase karne ke liye:</b>\n"
        f"{SEP}  DM karo: {CONTACT_DEV}\n"
        f"{SEP}\n"
        "╚══════════════════════════╝\n"
        f"{premium_footer()}"
    )
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("Buy Now - Developer DM", url="https://t.me/abhi09hub"))
    kb.add(types.InlineKeyboardButton("Channel join karo", url="https://t.me/abhihub09"))
    kb.add(types.InlineKeyboardButton("Back to Purchase Menu", callback_data="purchase_back"))
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        bot_send(call.message.chat.id, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "purchase_back")
def cb_purchase_back(call):
    bot.answer_callback_query(call.id)
    body = (
        f"Yaha se aap API kharid sakte hain.\n\n"
        f"<b>Available APIs:</b>\n"
        f"1. Number Info API\n\n"
        f"<i>Baaki APIs (TG, Vehicle, Aadhar) coming soon.</i>\n\n"
        f"<code>{'─' * 22}</code>\n"
        f"Kis API ki pricing dekhni hai? Niche choose karo."
    )
    txt = box("🛒", "PURCHASE API", body) + premium_footer()
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=purchase_kb())
    except Exception:
        bot_send(call.message.chat.id, txt, reply_markup=purchase_kb())

@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.from_user.id
    ensure_user(uid)
    update_user_meta(uid, message.from_user.first_name, message.from_user.username)
    if is_banned(uid):
        bot_reply(message, "Aap banned hain.")
        return
    if not is_bot_enabled():
        bot_reply(message, "Bot offline hai.")
        return
    if not all_force_joined(uid):
        require_join(message)
        return
    try:
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) == 2 and parts[1].strip().isdigit():
            ref = int(parts[1].strip())
            u   = get_user(uid)
            if ref != uid and u.get("referrer") is None:
                with db_lock:
                    db["users"][str(uid)]["referrer"]   = ref
                    ensure_user(ref)
                    db["users"][str(ref)]["referrals"] += 1
                    db["users"][str(ref)]["credits"]   += REFERRER_BONUS
                    db["users"][str(uid)]["credits"]   += REFEREE_BONUS
                    save_db()
                try:
                    bot.send_message(
                        ref,
                        slim_box("🎉", "REFERRAL BONUS",
                            f"Kisi ne aapka referral use kiya!\n"
                            f"+{REFERRER_BONUS} credits add hue."
                        ) + premium_footer()
                    )
                except Exception:
                    pass
    except Exception:
        pass
    send_welcome(message.chat.id, uid, message.from_user.first_name)

@bot.message_handler(commands=["help"])
def cmd_help(message):
    if not gate(message):
        return
    text = (
        "╔══════════════════════════╗\n"
        f"{SEP}  <b>ALL COMMANDS</b>\n"
        f"{SEP}  <code>{'═' * 24}</code>\n"
        f"{SEP}\n"
        f"{SEP}  <b>LOOKUP</b>\n"
        f"{SEP}  /num 9876543210\n"
        f"{SEP}\n"
        f"{SEP}  <b>ECONOMY</b>\n"
        f"{SEP}  /credits  - Balance dekho\n"
        f"{SEP}  /spin     - Daily reward\n"
        f"{SEP}  /redeem   - Code use karo\n"
        f"{SEP}  /refer    - Referral link\n"
        f"{SEP}\n"
        f"{SEP}  <b>ACCOUNT</b>\n"
        f"{SEP}  /profile  - Apna profile\n"
        f"{SEP}  /buy      - Purchase API\n"
        f"{SEP}  /dev      - Developer info\n"
        f"{SEP}\n"
        f"{SEP}  <i>Cost: {CREDITS_PER_LOOKUP} cr / lookup</i>\n"
        f"{SEP}  <i>Premium: Unlimited</i>\n"
        f"{SEP}\n"
        "╚══════════════════════════╝"
        f"{premium_footer()}"
    )
    bot_send(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(commands=["buy", "purchase"])
def cmd_buy(message):
    if not gate(message):
        return
    send_purchase_menu(message)

@bot.message_handler(commands=["credits"])
def cmd_credits(message):
    if not gate(message):
        return
    u   = get_user(message.from_user.id)
    cr  = u["credits"]
    bar = credit_bar(cr)
    prem = "<b>PREMIUM</b> - Unlimited lookups" if u["premium"] else "Free tier"
    text = box("💰", "YOUR CREDITS",
        f"{prem}\n\n"
        f"Balance:  [{bar}]  <b>{cr} cr</b>\n"
        f"Lookups:  {u['lookups']}\n"
        f"Refers:   {u['referrals']}\n\n"
        f"Earn: /spin  /refer  /redeem"
    ) + premium_footer()
    bot_send(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(commands=["spin"])
def cmd_spin(message):
    if not gate(message):
        return
    uid = message.from_user.id
    u   = get_user(uid)
    now = int(time.time())
    last = u.get("last_spin_at")
    spins_today = u.get("daily_spin_count", 0)
    if last:
        elapsed_hrs = (now - last) / 3600
        if elapsed_hrs < SPIN_COOLDOWN_HOURS and spins_today >= MAX_DAILY_SPINS:
            next_reset = last + (SPIN_COOLDOWN_HOURS * 3600)
            rem_min    = max(0, int((next_reset - now) / 60))
            h, m_      = divmod(rem_min, 60)
            bot_reply(message,
                box("⏰", "SPIN COOLDOWN",
                    f"Aaj ke spins khatam.\n\n"
                    f"Next reset: <b>{h}h {m_}m</b>\n"
                    f"Spins left: 0 / {MAX_DAILY_SPINS}"
                ) + premium_footer(), reply_markup=main_keyboard())
            return
    frames = ["🎰  . . .", "🎰  X . .", "🎰  X X .",
              "🎰  X X X", "🎰  * * *", "🎰  + + +"]
    m_msg = bot_send(message.chat.id, f"<code>{frames[0]}</code>")
    for fr in frames[1:]:
        time.sleep(0.35)
        try:
            bot.edit_message_text(f"<code>{fr}</code>", message.chat.id, m_msg.message_id)
        except Exception:
            pass
    r = random.random()
    if r < 0.55:
        gained, tier = random.randint(1, 2),  "Common"
    elif r < 0.80:
        gained, tier = random.randint(3, 4),  "Uncommon"
    elif r < 0.95:
        gained, tier = random.randint(5, 7),  "Rare"
    else:
        gained, tier = random.randint(8, 12), "JACKPOT"
    with db_lock:
        db["users"][str(uid)]["credits"]          += gained
        db["users"][str(uid)]["last_spin_at"]      = now
        db["users"][str(uid)]["daily_spin_count"]  = spins_today + 1
        save_db()
    global_stat_bump("total_spins")
    new_cr = get_user(uid)["credits"]
    left   = MAX_DAILY_SPINS - (spins_today + 1)
    try:
        bot.edit_message_text(
            box("🎰", "SPIN RESULT",
                f"Tier:    <b>{tier}</b>\n"
                f"Earned:  <b>+{gained} credits</b>\n"
                f"Balance: [{credit_bar(new_cr)}]  {new_cr} cr\n\n"
                f"Spins left today: {max(left, 0)} / {MAX_DAILY_SPINS}"
            ) + premium_footer(),
            message.chat.id, m_msg.message_id,
        )
    except Exception:
        pass

@bot.message_handler(commands=["profile"])
def cmd_profile(message):
    if not gate(message):
        return
    uid = message.from_user.id
    u   = get_user(uid)
    update_user_meta(uid, message.from_user.first_name, message.from_user.username)
    prem   = "PREMIUM" if u["premium"] else "Free"
    cr     = u["credits"]
    joined = (datetime.fromtimestamp(u.get("joined_at", 0)).strftime("%d %b %Y")
              if u.get("joined_at") else "-")
    uname  = f"@{message.from_user.username}" if message.from_user.username else "-"
    ref    = f"https://t.me/{bot.get_me().username}?start={uid}"
    body = (
        f"{message.from_user.first_name}  ({uname})\n"
        f"ID:  <code>{uid}</code>\n\n"
        f"Status:    {prem}\n"
        f"Credits:   [{credit_bar(cr)}]  {cr}\n"
        f"Lookups:   {u['lookups']}\n"
        f"Referrals: {u['referrals']}\n"
        f"Joined:    {joined}\n\n"
        f"Referral Link:\n<code>{ref}</code>"
    )
    txt = box("👤", "YOUR PROFILE", body) + premium_footer()
    sent = False
    try:
        photos = bot.get_user_profile_photos(uid, limit=1)
        if getattr(photos, "total_count", 0) > 0:
            fid = photos.photos[0][-1].file_id
            m   = bot.send_photo(message.chat.id, fid, caption=txt, reply_markup=main_keyboard())
            schedule_delete(message.chat.id, m.message_id)
            sent = True
    except Exception:
        pass
    if not sent:
        bot_send(message.chat.id, txt, reply_markup=main_keyboard())

@bot.message_handler(commands=["refer"])
def cmd_refer(message):
    if not gate(message):
        return
    uid = message.from_user.id
    u   = get_user(uid)
    ref = f"https://t.me/{bot.get_me().username}?start={uid}"
    text = box("🔗", "REFERRAL PROGRAM",
        f"Apna link share karo - credits jito!\n\n"
        f"Your Link:\n<code>{ref}</code>\n\n"
        f"Aap kamao:   <b>+{REFERRER_BONUS} cr</b> per referral\n"
        f"Woh paate:   <b>+{REFEREE_BONUS} cr</b> on join\n\n"
        f"Total Referrals: <b>{u['referrals']}</b>"
    ) + premium_footer()
    bot_send(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(commands=["redeem"])
def cmd_redeem(message):
    if not gate(message):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        bot_reply(message,
            slim_box("🎁", "REDEEM CODE", "Usage: /redeem YOUR_CODE") + premium_footer(),
            reply_markup=main_keyboard())
        return
    ok, msg = redeem_code(message.from_user.id, parts[1].strip())
    e = "✅" if ok else "❌"
    bot_reply(message, box(e, "CODE REDEEM", msg) + premium_footer(), reply_markup=main_keyboard())

@bot.message_handler(commands=["dev"])
def cmd_dev(message):
    if not gate(message):
        return
    text = box("👨‍💻", "DEVELOPER INFO",
        f"Dev:      {DEVELOPER}\n"
        f"Channel:  {CONTACT_CHANNEL}\n"
        f"Group:    {CONTACT_GROUP}\n\n"
        f"<i>DM for support, premium, ya custom bots.</i>"
    ) + premium_footer()
    bot_send(message.chat.id, text, reply_markup=contact_kb())

def _do_number_lookup(message, number: str):
    label = f"NUMBER: {number}"
    emoji = "📞"
    if not lookup_cost_and_consume(message.from_user.id):
        u  = get_user(message.from_user.id)
        cr = u["credits"]
        bot_reply(message,
            box("❌", "INSUFFICIENT CREDITS",
                f"Chahiye: <b>{CREDITS_PER_LOOKUP} cr</b>\n"
                f"Hai:     <b>{cr} cr</b>  [{credit_bar(cr)}]\n\n"
                "Earn karo: /spin  /refer  /redeem"
            ) + premium_footer(), reply_markup=main_keyboard())
        return
    try_react(message.chat.id, message.message_id, "👀")
    m_msg = bot.send_message(message.chat.id, f"<code>◐  {label}...</code>")
    stop_evt = threading.Event()
    anim_t   = threading.Thread(
        target=_animate_search,
        args=(message.chat.id, m_msg.message_id, label, stop_evt),
        daemon=True,
    )
    anim_t.start()
    try:
        res = api_number_lookup(number)
        stop_evt.set()
        try_react(message.chat.id, message.message_id, "✅")
    except Exception as e:
        stop_evt.set()
        try:
            bot.edit_message_text(
                box("⚠️", f"{label} FAILED", str(e)[:300]) + premium_footer(),
                message.chat.id, m_msg.message_id,
            )
        except Exception:
            pass
        return
    with db_lock:
        db["users"][str(message.from_user.id)]["lookups"] += 1
        save_db()
    global_stat_bump("total_lookups")
    body = fmt_records(res)
    try:
        bot.edit_message_text(
            box(emoji, label, body) + premium_footer(),
            message.chat.id, m_msg.message_id,
            reply_markup=main_keyboard(),
        )
    except Exception:
        bot_send(message.chat.id,
                 box(emoji, label, body) + premium_footer(),
                 reply_markup=main_keyboard())
    schedule_delete(message.chat.id, m_msg.message_id)

@bot.message_handler(commands=["num"])
def cmd_num(message):
    if not gate(message): return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        bot_reply(message, "Usage: <code>/num 9876543210</code>", reply_markup=main_keyboard()); return
    number = "".join(c for c in parts[1] if c.isdigit())
    if len(number) < 10:
        bot_reply(message, "Invalid number.", reply_markup=main_keyboard()); return
    _do_number_lookup(message, number)

@bot.message_handler(commands=["tg"])
def cmd_tg(message):
    if not gate(message): return
    send_coming_soon(message, "TG Lookup")

@bot.message_handler(commands=["veh"])
def cmd_veh(message):
    if not gate(message): return
    send_coming_soon(message, "Vehicle Info")

@bot.message_handler(commands=["aadhar"])
def cmd_aadhar(message):
    if not gate(message): return
    send_coming_soon(message, "Aadhar Info")

@bot.message_handler(commands=["owner"])
def cmd_owner(message):
    if not owner_gate(message): return
    total_u   = len(db.get("users", {}))
    total_b   = len(db.get("banned", {}))
    total_l   = db.get("stats", {}).get("total_lookups", 0)
    total_s   = db.get("stats", {}).get("total_spins", 0)
    total_p   = sum(1 for u in db.get("users", {}).values() if u.get("premium"))
    status    = "ONLINE" if is_bot_enabled() else "OFFLINE"
    header = (
        f"Bot:       {status}\n"
        f"Users:     {total_u}  |  Banned: {total_b}\n"
        f"Premium:   {total_p}\n"
        f"Lookups:   {total_l}  |  Spins: {total_s}"
    )
    bot_send(message.chat.id,
             box("👑", "OWNER PANEL", header) + premium_footer(),
             reply_markup=owner_panel_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("owner_"))
def owner_cb(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "Unauthorized.", show_alert=True)
        return
    d = call.data
    if d == "owner_toggle":
        new    = not is_bot_enabled()
        set_bot_enabled(new)
        status = "ONLINE" if new else "OFFLINE"
        bot.answer_callback_query(call.id, f"Bot is now {status}")
    elif d == "owner_banlist":
        bans = db.get("banned", {})
        txt  = "No banned users." if not bans else "\n".join(
            f"• <code>{uid}</code>:  {reason}" for uid, reason in bans.items())
        bot.answer_callback_query(call.id)
        bot_send(call.message.chat.id, box("🛑", "BAN LIST", txt) + premium_footer())
    elif d == "owner_stats":
        bot.answer_callback_query(call.id)
        total_u = len(db.get("users", {}))
        total_p = sum(1 for u in db.get("users", {}).values() if u.get("premium"))
        total_l = db.get("stats", {}).get("total_lookups", 0)
        total_s = db.get("stats", {}).get("total_spins", 0)
        txt = (
            f"Total Users:   <b>{total_u}</b>\n"
            f"Premium:       <b>{total_p}</b>\n"
            f"Banned:        <b>{len(db.get('banned', {}))}</b>\n"
            f"Total Lookups: <b>{total_l}</b>\n"
            f"Total Spins:   <b>{total_s}</b>"
        )
        bot_send(call.message.chat.id, box("📊", "BOT STATISTICS", txt) + premium_footer())
    else:
        hints = {
            "owner_addcredits": "Use: /addcredits <uid> <amount>",
            "owner_premium":    "Use: /premium <uid> <0|1>",
            "owner_checkuser":  "Use: /checkuser <uid>",
            "owner_ban":        "Use: /ban <uid> <reason>  ya  /unban <uid>",
            "owner_createcode": "Use: /createcode <CODE> <credits> <premium0|1> <uses>",
            "owner_broadcast":  "Use: /broadcast <text>",
        }
        bot.answer_callback_query(call.id, hints.get(d, "Unknown"), show_alert=True)

@bot.message_handler(commands=["addcredits"])
def cmd_addcredits(message):
    if not owner_gate(message): return
    parts = (message.text or "").split()
    if len(parts) < 3:
        bot_reply(message, "Usage: /addcredits <uid> <amount>"); return
    try:
        uid, amt = int(parts[1]), int(parts[2])
    except Exception:
        bot_reply(message, "uid aur amount integer hone chahiye."); return
    add_credits(uid, amt)
    sign = "+" if amt > 0 else ""
    bot_reply(message,
        box("💰", "CREDITS UPDATED",
            f"User:  <code>{uid}</code>\n"
            f"Delta: <b>{sign}{amt}</b>\n"
            f"New:   {get_user(uid)['credits']} cr"
        ) + premium_footer())

@bot.message_handler(commands=["premium"])
def cmd_premium_owner(message):
    if not owner_gate(message): return
    parts = (message.text or "").split()
    if len(parts) < 3:
        bot_reply(message, "Usage: /premium <uid> <0|1>"); return
    try:
        uid = int(parts[1])
    except Exception:
        bot_reply(message, "uid integer hona chahiye."); return
    val = parts[2].strip().lower() in ("1", "true", "yes", "on")
    set_premium(uid, val)
    bot_reply(message,
        box("👑", "PREMIUM UPDATED",
            f"User:    <code>{uid}</code>\n"
            f"Premium: {'ON' if val else 'OFF'}"
        ) + premium_footer())

@bot.message_handler(commands=["checkuser"])
def cmd_checkuser(message):
    if not owner_gate(message): return
    parts = (message.text or "").split()
    if len(parts) < 2:
        bot_reply(message, "Usage: /checkuser <uid>"); return
    try:
        uid = int(parts[1])
    except Exception:
        bot_reply(message, "uid integer hona chahiye."); return
    u      = get_user(uid)
    joined = (datetime.fromtimestamp(u.get("joined_at", 0)).strftime("%d %b %Y")
              if u.get("joined_at") else "-")
    body = (
        f"UID:      <code>{uid}</code>\n"
        f"Name:     {u.get('first_name', '-')}\n"
        f"Username: @{u.get('username', '-')}\n\n"
        f"Credits:  [{credit_bar(u['credits'])}]  {u['credits']}\n"
        f"Premium:  {'Yes' if u['premium'] else 'No'}\n"
        f"Lookups:  {u['lookups']}\n"
        f"Refers:   {u['referrals']}\n"
        f"Spins:    {u['daily_spin_count']}\n"
        f"Joined:   {joined}\n"
        f"Banned:   {'Yes' if is_banned(uid) else 'No'}"
    )
    bot_reply(message, box("🔎", "USER INFO", body) + premium_footer())

@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if not owner_gate(message): return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 2:
        bot_reply(message, "Usage: /ban <uid> <reason>"); return
    try:
        uid = int(parts[1])
    except Exception:
        bot_reply(message, "uid integer hona chahiye."); return
    reason = parts[2] if len(parts) >= 3 else "No reason"
    with db_lock:
        db["banned"][str(uid)] = reason
        save_db()
    bot_reply(message,
        box("🛑", "USER BANNED",
            f"User:   <code>{uid}</code>\n"
            f"Reason: {reason}"
        ) + premium_footer())

@bot.message_handler(commands=["unban"])
def cmd_unban(message):
    if not owner_gate(message): return
    parts = (message.text or "").split()
    if len(parts) < 2:
        bot_reply(message, "Usage: /unban <uid>"); return
    try:
        uid = int(parts[1])
    except Exception:
        bot_reply(message, "uid integer hona chahiye."); return
    with db_lock:
        db["banned"].pop(str(uid), None)
        save_db()
    bot_reply(message,
        box("✅", "USER UNBANNED", f"User: <code>{uid}</code>") + premium_footer())

@bot.message_handler(commands=["createcode"])
def cmd_createcode(message):
    if not owner_gate(message): return
    parts = (message.text or "").split()
    if len(parts) < 5:
        bot_reply(message, "Usage: /createcode <CODE> <credits> <premium0|1> <uses>"); return
    code = parts[1]
    try:
        credits_ = int(parts[2])
        uses_    = int(parts[4])
    except Exception:
        bot_reply(message, "credits aur uses integer hone chahiye."); return
    prem = parts[3].strip().lower() in ("1", "true", "yes", "on")
    create_code(code, credits=credits_, premium=prem, uses=uses_)
    bot_reply(message,
        box("🎁", "CODE CREATED",
            f"Code:    <code>{code}</code>\n"
            f"Credits: +{credits_}\n"
            f"Premium: {'Yes' if prem else 'No'}\n"
            f"Uses:    {uses_}"
        ) + premium_footer())

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message):
    if not owner_gate(message): return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        bot_reply(message, "Usage: /broadcast <text>"); return
    text     = parts[1]
    user_ids = list(db.get("users", {}).keys())
    sent = failed = 0
    for uid_s in user_ids:
        try:
            bot.send_message(int(uid_s), text, reply_markup=main_keyboard())
            sent += 1
        except Exception:
            failed += 1
        time.sleep(0.05)
    bot_reply(message,
        box("📣", "BROADCAST DONE",
            f"Sent:   <b>{sent}</b>\n"
            f"Failed: <b>{failed}</b>\n"
            f"Total:  <b>{len(user_ids)}</b>"
        ) + premium_footer())

KEYBOARD_MAP = {
    "TG LOOKUP":     lambda m: send_coming_soon(m, "TG Lookup"),
    "NUMBER INFO":   lambda m: bot_reply(m, "Usage: <code>/num 9876543210</code>", reply_markup=main_keyboard()),
    "VEHICLE INFO":  lambda m: send_coming_soon(m, "Vehicle Info"),
    "AADHAR INFO":   lambda m: send_coming_soon(m, "Aadhar Info"),
    "MY CREDITS":    cmd_credits,
    "DAILY SPIN":    cmd_spin,
    "PROFILE":       cmd_profile,
    "HELP":          cmd_help,
    "PURCHASE API":  cmd_buy,
    "CONTACT DEV":   cmd_dev,
}

@bot.message_handler(content_types=["text"])
def router(message):
    if should_suppress(message):
        return
    txt = (message.text or "").strip()
    if txt in KEYBOARD_MAP:
        KEYBOARD_MAP[txt](message)
        return
    if not txt.startswith("/"):
        if is_banned(message.from_user.id):
            bot_reply(message, "Aap banned hain.")
            return
        if all_force_joined(message.from_user.id):
            bot_reply(message, "Use /help ya niche ke buttons.", reply_markup=main_keyboard())
        else:
            require_join(message)

def main():
    load_db()
    print(f"{BOT_NAME} {BOT_VERS} - Live!")
    bot.infinity_polling(timeout=API_TIMEOUT_SEC, long_polling_timeout=API_TIMEOUT_SEC)

if __name__ == "__main__":
    main()
