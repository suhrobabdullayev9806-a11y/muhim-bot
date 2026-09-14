import json
import os
import sqlite3
import threading
import time

import telebot
from telebot import types

ADMIN_PASSWORD = "admin123"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stars_bot.db")


def _load_bot_token():
    token = os.environ.get("BOT_TOKEN", "").strip()
    if token and token != "PUT_YOUR_BOT_TOKEN_HERE":
        return token
    tf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BOT_TOKEN.txt")
    if os.path.exists(tf):
        try:
            with open(tf, encoding="utf-8") as f:
                token = f.read().strip()
            if token:
                return token
        except OSError:
            pass
    return "8778433451:AAFqHopgkqjqlGIM_wVDwQtLc7fOJKyoWeU"


BOT_TOKEN = _load_bot_token()
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

BOT_USERNAME = ""

EMOJI = {
    "star": ("5438496463044752972", "\u2b50"),
    "crown": ("5217822164362739968", "\U0001f451"),
    "diamond": ("5427168083074628963", "\U0001f48e"),
    "fire": ("5424972470023104089", "\U0001f525"),
    "bolt": ("5456140674028019486", "\u26a1"),
    "link": ("5271604874419647061", "\U0001f517"),
    "megaphone": ("5424818078833715060", "\U0001f4e3"),
    "bell": ("5458603043203327669", "\U0001f514"),
    "check": ("5206607081334906820", "\u2714"),
    "cross": ("5210952531676504517", "\u274c"),
    "warn": ("5447644880824181073", "\u26a0"),
    "chart": ("5231200819986047254", "\U0001f4ca"),
    "money": ("5233326571099534068", "\U0001f4b8"),
    "coin": ("5409048419211682843", "\U0001f4b5"),
    "confetti": ("5461151367559141950", "\U0001f389"),
    "idea": ("5422439311196834318", "\U0001f4a1"),
    "new": ("5382357040008021292", "\U0001f195"),
    "lock": ("5296369303661067030", "\U0001f512"),
    "shopping": ("5224607267797606837", "\U0001f6cd"),
    "gear": ("5341715473882955310", "\u2699\ufe0f"),
}


def P(key):
    if key in EMOJI:
        eid, fb = EMOJI[key]
        return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'
    return key


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 0,
        referred_by INTEGER,
        step TEXT DEFAULT 'home'
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    defaults = {
        "req_stars": "21",
        "gift_amount": "15",
        "ref_bonus": "1",
        "gift_id": "",
        "payment_channel": "@sizning_kanal",
        "support_username": "@sizning_support",
        "admin_id": "",
        "mandatory_channel": "",
    }
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", (k, v))
    conn.commit()
    conn.close()


def get_setting(key, default=""):
    conn = db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = db()
    conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


def register_user(user_id, username, referred_by=None):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users(user_id, username, balance, referred_by, step) VALUES(?,?,?,?,?)",
        (user_id, username, 0, referred_by, "home"),
    )
    if username:
        cur.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
    conn.commit()
    conn.close()


def get_balance(user_id):
    conn = db()
    row = conn.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row["balance"] if row else 0


def set_balance(user_id, amount):
    conn = db()
    conn.execute("UPDATE users SET balance=? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()


def add_balance(user_id, amount):
    conn = db()
    conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()


def get_step(user_id):
    conn = db()
    row = conn.execute("SELECT step FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row["step"] if row else "home"


def set_step(user_id, step):
    conn = db()
    conn.execute("UPDATE users SET step=? WHERE user_id=?", (step, user_id))
    conn.commit()
    conn.close()


def is_admin(user_id):
    admin_id = get_setting("admin_id", "")
    return admin_id != "" and str(user_id) == str(admin_id)


def _norm_channel(raw):
    ch = (raw or "").strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if ch.lower().startswith(prefix):
            ch = ch[len(prefix):]
    ch = ch.split("/")[0].split("?")[0].strip()
    if ch and not ch.startswith("@"):
        ch = "@" + ch
    return ch


def check_subscription(user_id):
    channel = _norm_channel(get_setting("mandatory_channel", ""))
    if not channel:
        return True
    try:
        member = bot.get_chat_member(channel, user_id)
        return member.status in ("member", "administrator", "creator", "restricted")
    except telebot.apihelper.ApiException as exc:
        admin_id = get_setting("admin_id", "")
        try:
            if admin_id:
                bot.send_message(
                    admin_id,
                    f"{P('warn')} <b>Obuna tekshiruv xatolik</b>\n\n"
                    f"Kanal: <code>{channel}</code>\n"
                    f"Xatolik: <code>{str(exc)[:200]}</code>\n\n"
                    f"{P('idea')} Bot kanalda <b>admin</b> bo'lishi shart!"
                    f"Kanal nomi to'g'riligini tekshiring.",
                )
        except Exception:
            pass
        return False


def build_subscribe_panel():
    ch = _norm_channel(get_setting("mandatory_channel", "")).lstrip("@")
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton(
            "Kanalga a'zo bo'lish",
            url=f"https://t.me/{ch}" if ch else "https://t.me/",
            icon_custom_emoji_id="5296369303661067030",
            style="primary",
        ),
        types.InlineKeyboardButton(
            "Obunani tekshirish",
            callback_data="sub:check",
            icon_custom_emoji_id="5206607081334906820",
            style="success",
        ),
    )
    return kb


def check_and_prompt(message):
    uid = message.from_user.id
    if check_subscription(uid):
        return True
    channel = get_setting("mandatory_channel", "").strip()
    bot.send_message(
        uid,
        f"{P('lock')} <b>Majburiy obuna</b>\n\n"
        f"{P('warn')} Botdan foydalanish uchun kanalimizga a'zo bo'ling:\n{channel}\n\n"
        f"Obuna bo'lgach obunani tekshiring.",
        reply_markup=build_subscribe_panel(),
    )
    return False


BTN = {
    "Stars ishlash": "5438496463044752972",
    "Hisobim": "5217822164362739968",
    "Stars yechish": "5456140674028019486",
    "To'lov Kanali": "5424818078833715060",
    "Murojaat": "5271604874419647061",
    "Qo'llanma": "5427168083074628963",
}


def build_btn(text, style="primary", icon=None):
    kwargs = {"text": text, "style": style}
    if icon:
        kwargs["icon_custom_emoji_id"] = icon
    return types.KeyboardButton(**kwargs)


def menu_default():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(build_btn("Stars ishlash", "primary", BTN["Stars ishlash"]))
    kb.row(
        build_btn("Hisobim", "primary", BTN["Hisobim"]),
        build_btn("Stars yechish", "primary", BTN["Stars yechish"]),
    )
    kb.row(build_btn("To'lov Kanali", "primary", BTN["To'lov Kanali"]))
    kb.row(
        build_btn("Murojaat", "primary", BTN["Murojaat"]),
        build_btn("Qo'llanma", "primary", BTN["Qo'llanma"]),
    )
    return kb


def menu_stars_active():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(build_btn("Stars ishlash", "success", BTN["Stars ishlash"]))
    kb.row(
        build_btn("Hisobim", "primary", BTN["Hisobim"]),
        build_btn("Stars yechish", "primary", BTN["Stars yechish"]),
    )
    kb.row(build_btn("To'lov Kanali", "primary", BTN["To'lov Kanali"]))
    kb.row(
        build_btn("Murojaat", "primary", BTN["Murojaat"]),
        build_btn("Qo'llanma", "primary", BTN["Qo'llanma"]),
    )
    return kb


def menu_hisob_active():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(build_btn("Stars ishlash", "primary", BTN["Stars ishlash"]))
    kb.row(
        build_btn("Hisobim", "success", BTN["Hisobim"]),
        build_btn("Stars yechish", "primary", BTN["Stars yechish"]),
    )
    kb.row(build_btn("To'lov Kanali", "primary", BTN["To'lov Kanali"]))
    kb.row(
        build_btn("Murojaat", "primary", BTN["Murojaat"]),
        build_btn("Qo'llanma", "primary", BTN["Qo'llanma"]),
    )
    return kb


def menu_yechish_active():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(build_btn("Stars ishlash", "primary", BTN["Stars ishlash"]))
    kb.row(
        build_btn("Hisobim", "primary", BTN["Hisobim"]),
        build_btn("Stars yechish", "danger", BTN["Stars yechish"]),
    )
    kb.row(build_btn("To'lov Kanali", "primary", BTN["To'lov Kanali"]))
    kb.row(
        build_btn("Murojaat", "primary", BTN["Murojaat"]),
        build_btn("Qo'llanma", "primary", BTN["Qo'llanma"]),
    )
    return kb


ICO = {
    "gear": "5341715473882955310",
    "shopping": "5224607267797606837",
    "diamond": "5427168083074628963",
    "megaphone": "5424818078833715060",
    "chart": "5231200819986047254",
    "lock": "5296369303661067030",
    "star": "5438496463044752972",
    "link": "5271604874419647061",
    "crown": "5217822164362739968",
    "money": "5233326571099534068",
    "coin": "5409048419211682843",
    "bell": "5458603043203327669",
    "cross": "5210952531676504517",
}


def ibtn(text, data, icon, style="primary"):
    return types.InlineKeyboardButton(
        text=text,
        callback_data=data,
        icon_custom_emoji_id=ICO[icon],
        style=style,
    )


def build_admin_panel():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        ibtn("Yechish sharti", "set:req", "gear", "success"),
        ibtn("Gift soni", "set:gift", "shopping", "success"),
        ibtn("Gift ID", "set:giftid", "diamond", "success"),
        ibtn("Referal bonus", "set:ref", "coin", "success"),
        ibtn("Majburiy obuna kanal", "set:channel", "lock", "primary"),
        ibtn("Kanalni o'chirish", "set:channel_del", "cross", "danger"),
        ibtn("To'lov Kanali", "set:paychan", "megaphone", "primary"),
        ibtn("Murojaat", "set:support", "bell", "primary"),
        ibtn("Reklama tarqatish", "set:adv", "megaphone", "primary"),
        ibtn("Statistika", "set:stats", "chart", "primary"),
        ibtn("Bot balansini to'ldirish", "set:botbal", "money", "success"),
        ibtn("Chiqish", "set:exit", "lock", "danger"),
    )
    return kb


def build_topup():
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.row(
        types.InlineKeyboardButton("50 \u2b50", callback_data="pay:50"),
        types.InlineKeyboardButton("100 \u2b50", callback_data="pay:100"),
        types.InlineKeyboardButton("200 \u2b50", callback_data="pay:200"),
    )
    kb.row(
        types.InlineKeyboardButton("500 \u2b50", callback_data="pay:500"),
        types.InlineKeyboardButton("1000 \u2b50", callback_data="pay:1000"),
    )
    return kb


@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.from_user.id
    username = message.from_user.username
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        try:
            referred_by = int(args[1])
        except ValueError:
            referred_by = None
    register_user(uid, username, referred_by)
    set_step(uid, "home")
    if referred_by and referred_by != uid:
        bonus = int(get_setting("ref_bonus", "1"))
        add_balance(referred_by, bonus)
        try:
            bot.send_message(
                referred_by,
                f"{P('confetti')} Sizning havolangiz orqali yangi foydalanuvchi kirdi!\n"
                f"+{bonus} {P('star')} hisobingizga qo'shildi.",
            )
        except Exception:
            pass
    if not check_subscription(uid):
        bot.send_message(
            uid,
            f"{P('lock')} <b>Majburiy obuna</b>\n\n"
            f"{P('warn')} Botdan foydalanish uchun kanalimizga a'zo bo'ling:\n"
            f"{get_setting('mandatory_channel', '')}\n\n"
            f"Obuna bo'lgach obunani tekshiring.",
            reply_markup=build_subscribe_panel(),
        )
        return
    bot.send_message(
        uid,
        f"{P('star')} <b>Xush kelibsiz!</b>\n\n"
        f"Bu bot orqali Telegram {P('star')} ishlashingiz va o'zingiz tanlagan odamga "
        f"{P('shopping')} sovg'a (Gift) yuborishingiz mumkin.\n\n"
        f"Quyidagi menyudan kerakli bo'limni tanlang",
        reply_markup=menu_default(),
    )


@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("/akam"))
def cmd_akam(message):
    uid = message.from_user.id
    parts = message.text.split()
    if len(parts) < 2 or parts[1] != ADMIN_PASSWORD:
        bot.send_message(uid, f"{P('cross')} Parol noto'g'ri!")
        return
    set_setting("admin_id", str(uid))
    set_step(uid, "admin")
    bot.send_message(uid, f"{P('crown')} Admin panelga xush kelibsiz!", reply_markup=build_admin_panel())


@bot.message_handler(func=lambda m: get_step(m.from_user.id) == "await_username", content_types=["text"])
def handle_withdraw_username(message):
    uid = message.from_user.id
    set_step(uid, "home")
    username = message.text.strip().lstrip("@")
    req_stars = int(get_setting("req_stars", "21"))
    balance = get_balance(uid)
    if balance < req_stars:
        missing = req_stars - balance
        bot.send_message(
            uid,
            f"{P('cross')} Hisobingizda yetarli stars yo'q!\n\n"
            f"{P('gear')} Yechish sharti: <b>{req_stars} {P('star')}</b>\n"
            f"{P('coin')} Sizda: <b>{balance} {P('star')}</b>\n"
            f"{P('warn')} Yetmayapti: <b>{missing} {P('star')}</b>",
            reply_markup=menu_default(),
        )
        return
    gift_id = get_setting("gift_id", "")
    if not gift_id:
        bot.send_message(uid, f"{P('cross')} Gift hozircha sozlanmagan.", reply_markup=menu_default())
        return
    try:
        target = bot.get_chat("@" + username)
        target_id = target.id
    except telebot.apihelper.ApiException:
        bot.send_message(
            uid,
            f"{P('warn')} @{username} topilmadi yoki bot bilan suhbatni boshlamagan.\n"
            f"{P('idea')} Qabul qiluvchi avval botga /start yuborishi kerak.",
            reply_markup=menu_default(),
        )
        return
    set_balance(uid, balance - req_stars)
    try:
        bot.send_gift(target_id, gift_id, text=None)
        gift_amount = get_setting("gift_amount", "15")
        bot.send_message(
            uid,
            f"{P('check')} Gift muvaffaqiyatli yuborildi!\n\n"
            f"{P('megaphone')} Qabul qiluvchi: @{username}\n"
            f"{P('shopping')} Gift: {gift_amount} {P('star')}\n"
            f"{P('money')} Hisobdan yechildi: {req_stars} {P('star')}\n"
            f"{P('coin')} Qolgan balans: {get_balance(uid)} {P('star')}",
            reply_markup=menu_default(),
        )
        admin_id = get_setting("admin_id", "")
        if admin_id:
            try:
                bot.send_message(
                    admin_id,
                    f"{P('bell')} <b>Yangi gift chiqarildi!</b>\n\n"
                    f"{P('coin')} Jo'natuvchi: {uid} (@{message.from_user.username})\n"
                    f"{P('megaphone')} Qabul qiluvchi: @{username}\n"
                    f"{P('shopping')} Gift: {gift_amount} {P('star')}\n"
                    f"{P('money')} Yechilgan: {req_stars} {P('star')}",
                )
            except Exception:
                pass
    except telebot.apihelper.ApiException as exc:
        set_balance(uid, get_balance(uid) + req_stars)
        err = str(exc.result_json) if exc.result_json else str(exc)
        bot.send_message(
            uid,
            f"{P('cross')} Gift yuborishda xatolik. Balans qaytarildi.\n\nXatolik: <code>{err[:200]}</code>",
            reply_markup=menu_default(),
        )
    except Exception:
        set_balance(uid, get_balance(uid) + req_stars)
        bot.send_message(uid, f"{P('cross')} Kutilmagan xatolik. Balans qaytarildi.", reply_markup=menu_default())


@bot.message_handler(content_types=["text"])
def handle_text(message):
    uid = message.from_user.id
    step = get_step(uid)
    if step.startswith("await_") and is_admin(uid):
        handle_admin_input(message)
        return
    if not check_and_prompt(message):
        return
    text = message.text.strip()
    if text == "Stars ishlash":
        bonus = get_setting("ref_bonus", "1")
        link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        bot.send_message(
            uid,
            f"{P('link')} <b>Referal tizimi!</b>\n\n"
            f"Do'stlaringizni taklif qiling va har bir kirgan odam uchun "
            f"<b>+{bonus} {P('star')}</b> oling.\n\n"
            f"{P('link')} Sizning havolangiz:\n<code>{link}</code>",
            reply_markup=menu_stars_active(),
        )
    elif text == "Hisobim":
        username = message.from_user.username or "yangi foydalanuvchi"
        conn = db()
        row = conn.execute("SELECT referred_by FROM users WHERE user_id=?", (uid,)).fetchone()
        conn.close()
        referred_by = row["referred_by"] if row and row["referred_by"] else "-"
        bot.send_message(
            uid,
            f"{P('crown')} <b>Hisobim</b>\n\n"
            f"{P('star')} ID: <code>{uid}</code>\n"
            f"{P('coin')} Username: @{username}\n"
            f"{P('money')} Balans: <b>{get_balance(uid)} {P('star')}</b>\n"
            f"{P('link')} Kim orqali kirdi: {referred_by}\n\n"
            f"Balansni to'ldirish uchun summani tanlang:",
            reply_markup=build_topup(),
        )
        bot.send_message(uid, "\U0001f447", reply_markup=menu_hisob_active())
    elif text == "Stars yechish":
        req_stars = int(get_setting("req_stars", "21"))
        balance = get_balance(uid)
        if balance >= req_stars:
            set_step(uid, "await_username")
            bot.send_message(
                uid,
                f"{P('shopping')} Gift yuboriladigan odamning Telegram <b>@username</b> yuboring.\n\n"
                f"{P('idea')} Qabul qiluvchi avval botga /start bosgan bo'lishi kerak!",
                reply_markup=menu_yechish_active(),
            )
        else:
            missing = req_stars - balance
            bot.send_message(
                uid,
                f"{P('warn')} Hisobingizda yetarli stars yo'q!\n\n"
                f"{P('gear')} Yechish sharti: <b>{req_stars} {P('star')}</b>\n"
                f"{P('coin')} Sizda: <b>{balance} {P('star')}</b>\n"
                f"{P('cross')} Yetmayapti: <b>{missing} {P('star')}</b>",
                reply_markup=menu_yechish_active(),
            )
    elif text == "To'lov Kanali":
        channel = get_setting("payment_channel", "@sizning_kanal")
        bot.send_message(
            uid,
            f"{P('megaphone')} <b>To'lov Kanali</b>\n\n{channel}",
            reply_markup=menu_default(),
        )
    elif text == "Murojaat":
        support = get_setting("support_username", "@sizning_support")
        bot.send_message(
            uid,
            f"{P('bell')} <b>Murojaat</b>\n\n{support}",
            reply_markup=menu_default(),
        )
    elif text == "Qo'llanma":
        req_stars = get_setting("req_stars", "21")
        gift_amount = get_setting("gift_amount", "15")
        bonus = get_setting("ref_bonus", "1")
        bot.send_message(
            uid,
            f"{P('idea')} <b>Qo'llanma</b>\n\n"
            f"1. {P('coin')} Hisobim orqali Stars to'ldiring.\n"
            f"2. {req_stars} {P('star')} yig'ganingizdan so'ng {P('bolt')} Stars yechish.\n"
            f"3. Gift yuboriladigan odamning @username yuboring.\n"
            f"4. Gift avtomatik yetkaziladi! {P('confetti')}\n\n"
            f"{P('gear')} Yechish sharti: <b>{req_stars} {P('star')}</b>\n"
            f"{P('shopping')} Gift miqdori: <b>{gift_amount} {P('star')}</b>\n"
            f"{P('link')} Referal bonusi: <b>+{bonus} {P('star')}</b>",
            reply_markup=menu_default(),
        )
    else:
        bot.send_message(uid, "Quyidagi menyudan tanlang:", reply_markup=menu_default())


def handle_admin_input(message):
    uid = message.from_user.id
    if not is_admin(uid):
        set_step(uid, "home")
        return
    step = get_step(uid)
    value = message.text.strip()
    try:
        if step == "await_req":
            n = int(value)
            if n <= 0:
                raise ValueError
            set_setting("req_stars", n)
            bot.send_message(uid, f"{P('check')} Yechish sharti: <b>{n} {P('star')}</b>", reply_markup=build_admin_panel())
        elif step == "await_gift":
            n = int(value)
            if n <= 0:
                raise ValueError
            set_setting("gift_amount", n)
            bot.send_message(uid, f"{P('check')} Gift soni: <b>{n} {P('star')}</b>", reply_markup=build_admin_panel())
        elif step == "await_giftid":
            set_setting("gift_id", value)
            bot.send_message(uid, f"{P('check')} Gift ID: <code>{value}</code>", reply_markup=build_admin_panel())
        elif step == "await_ref":
            n = int(value)
            if n <= 0:
                raise ValueError
            set_setting("ref_bonus", n)
            bot.send_message(uid, f"{P('check')} Referal bonusi: <b>+{n} {P('star')}</b>", reply_markup=build_admin_panel())
        elif step == "await_channel":
            if value in ("-", "0", "o'chirish", "delete"):
                set_setting("mandatory_channel", "")
                bot.send_message(uid, f"{P('cross')} Majburiy obuna <b>o'chirildi</b>.", reply_markup=build_admin_panel())
            else:
                set_setting("mandatory_channel", value)
                bot.send_message(uid, f"{P('check')} Majburiy obuna kanali: <code>{value}</code>", reply_markup=build_admin_panel())
        elif step == "await_paychan":
            set_setting("payment_channel", value)
            bot.send_message(uid, f"{P('check')} To'lov Kanali: <code>{value}</code>", reply_markup=build_admin_panel())
        elif step == "await_support":
            set_setting("support_username", value)
            bot.send_message(uid, f"{P('check')} Murojaat: <code>{value}</code>", reply_markup=build_admin_panel())
        elif step == "await_adv":
            conn = db()
            rows = conn.execute("SELECT user_id FROM users").fetchall()
            conn.close()
            ok, fail = 0, 0
            for row in rows:
                try:
                    bot.send_message(row["user_id"], f"{P('megaphone')} <b>Elon</b>\n\n{value}")
                    ok += 1
                except Exception:
                    fail += 1
            bot.send_message(
                uid,
                f"{P('check')} Tarqatildi: {ok}\n{P('cross')} O'tmadi: {fail}",
                reply_markup=build_admin_panel(),
            )
        set_step(uid, "admin")
    except (ValueError, TypeError):
        bot.send_message(uid, f"{P('cross')} Noto'g'ri qiymat. Qayta urinib ko'ring.", reply_markup=build_admin_panel())
    except Exception as exc:
        bot.send_message(uid, f"{P('cross')} Xatolik: {exc}", reply_markup=build_admin_panel())


@bot.callback_query_handler(func=lambda c: c.data.startswith("sub:"))
def on_sub_callback(call):
    uid = call.from_user.id
    if check_subscription(uid):
        bot.answer_callback_query(call.id, "Obuna tasdiqlandi!", show_alert=True)
        bot.send_message(uid, "Endi botdan foydalanishingiz mumkin:", reply_markup=menu_default())
    else:
        bot.answer_callback_query(call.id, "Hali obuna bo'lmadingiz!", show_alert=True)


@bot.callback_query_handler(func=lambda c: c.data.startswith("pay:"))
def on_pay_callback(call):
    uid = call.from_user.id
    try:
        stars = int(call.data.split(":")[1])
    except (ValueError, IndexError):
        bot.answer_callback_query(call.id, "Xato summa")
        return
    bot.answer_callback_query(call.id, "Chek ochilmoqda...")
    try:
        bot.send_invoice(
            chat_id=uid,
            title="Telegram Stars to'ldirish",
            description=f"Hisobingizga {stars} {P('star')} qo'shish",
            invoice_payload=f"topup:{uid}",
            provider_token="",
            currency="XTR",
            prices=[types.LabeledPrice(label="Telegram Stars", amount=stars)],
        )
    except Exception as exc:
        bot.send_message(uid, f"{P('cross')} Chek ochilmadi: {exc}")


@bot.callback_query_handler(func=lambda c: c.data.startswith("set:"))
def on_admin_callback(call):
    uid = call.from_user.id
    if not is_admin(uid):
        bot.answer_callback_query(call.id, "Siz admin emassiz!")
        return
    action = call.data.split(":")[1]
    mid = call.message.message_id
    if action == "req":
        set_step(uid, "await_req")
        bot.edit_message_text(
            f"{P('gear')} Yangi <b>req_stars</b> (yechish sharti) sonini yuboring\u2026",
            uid, mid,
        )
    elif action == "gift":
        set_step(uid, "await_gift")
        bot.edit_message_text(
            f"{P('shopping')} Yangi <b>gift_amount</b> sonini yuboring\u2026",
            uid, mid,
        )
    elif action == "giftid":
        set_step(uid, "await_giftid")
        bot.edit_message_text(
            f"{P('diamond')} Yangi <b>Gift ID</b> yuboring\u2026",
            uid, mid,
        )
    elif action == "ref":
        set_step(uid, "await_ref")
        bot.edit_message_text(
            f"{P('coin')} Yangi <b>referal bonusi</b> (star soni) yuboring\u2026",
            uid, mid,
        )
    elif action == "channel":
        set_step(uid, "await_channel")
        bot.edit_message_text(
            f"{P('lock')} Majburiy obuna <b>kanal username</b> yuboring (masalan @kanal_nomi):\n\n"
            f"Joriy: {get_setting('mandatory_channel', '') or 'yoqilmagan'}",
            uid, mid,
        )
    elif action == "channel_del":
        set_setting("mandatory_channel", "")
        set_step(uid, "admin")
        bot.edit_message_text(
            f"{P('cross')} Majburiy obuna <b>o'chirildi</b>.",
            uid, mid,
        )
        bot.send_message(uid, f"{P('crown')} Admin panel", reply_markup=build_admin_panel())
    elif action == "paychan":
        set_step(uid, "await_paychan")
        bot.edit_message_text(
            f"{P('megaphone')} Yangi <b>To'lov Kanali</b> yuboring (masalan @kanal_nomi):\n\n"
            f"Joriy: {get_setting('payment_channel', '@sizning_kanal')}",
            uid, mid,
        )
    elif action == "support":
        set_step(uid, "await_support")
        bot.edit_message_text(
            f"{P('bell')} Yangi <b>Murojaat</b> username yuboring (masalan @support_nomi):\n\n"
            f"Joriy: {get_setting('support_username', '@sizning_support')}",
            uid, mid,
        )
    elif action == "adv":
        set_step(uid, "await_adv")
        bot.edit_message_text(
            f"{P('megaphone')} Barcha foydalanuvchilarga yuboriladigan reklama matnini yozing\u2026",
            uid, mid,
        )
    elif action == "stats":
        conn = db()
        users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        total_bal = conn.execute("SELECT COALESCE(SUM(balance),0) s FROM users").fetchone()["s"]
        ref_count = conn.execute("SELECT COUNT(*) c FROM users WHERE referred_by IS NOT NULL").fetchone()["c"]
        conn.close()
        channel = get_setting("mandatory_channel", "").strip() or "yo'q"
        bot.answer_callback_query(call.id)
        bot.send_message(
            uid,
            f"{P('chart')} <b>Statistika</b>\n\n"
            f"{P('coin')} Foydalanuvchilar: {users}\n"
            f"{P('link')} Ref. orqali kirganlar: {ref_count}\n"
            f"{P('money')} Umumiy balans: {total_bal} {P('star')}\n\n"
            f"{P('gear')} Yechish sharti: {get_setting('req_stars')} {P('star')}\n"
            f"{P('shopping')} Gift: {get_setting('gift_amount')} {P('star')}\n"
            f"{P('coin')} Referal bonus: +{get_setting('ref_bonus')} {P('star')}\n"
            f"{P('diamond')} Gift ID: <code>{get_setting('gift_id')}</code>\n"
            f"{P('lock')} Obuna kanali: <code>{channel}</code>\n"
            f"{P('megaphone')} To'lov kanali: {get_setting('payment_channel', '@sizning_kanal')}\n"
            f"{P('bell')} Murojaat: {get_setting('support_username', '@sizning_support')}",
            reply_markup=build_admin_panel(),
        )
    elif action == "botbal":
        bot.answer_callback_query(call.id, "Invoice yuborilmoqda...")
        try:
            bot.send_invoice(
                chat_id=uid,
                title="Bot balansini to'ldirish",
                description="Stars bot balansiga qo'shiladi (gift yuborish uchun)",
                invoice_payload=f"botbal:{uid}",
                provider_token="",
                currency="XTR",
                prices=[types.LabeledPrice(label="Bot Stars", amount=50)],
            )
        except Exception as exc:
            bot.send_message(uid, f"{P('cross')} Chek ochilmadi: {exc}")
    elif action == "exit":
        set_step(uid, "home")
        bot.edit_message_text(f"{P('lock')} Admin paneldan chiqdingiz.", uid, mid)
        bot.send_message(uid, "Asosiy menyu:", reply_markup=menu_default())


@bot.pre_checkout_query_handler(func=lambda q: True)
def on_pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def on_successful_payment(message):
    uid = message.from_user.id
    payload = message.successful_payment.invoice_payload
    stars = message.successful_payment.total_amount
    if payload.startswith("botbal:"):
        bot_bal_text = ""
        try:
            bal_info = bot.get_my_star_balance()
            bot_bal_text = f"{P('coin')} Bot balans: {bal_info.balance} {P('star')}"
        except Exception:
            pass
        bot.send_message(
            uid,
            f"{P('check')} <b>Rahmat!</b>\n\n"
            f"{P('star')} {stars} {P('star')} bot balansiga qo'shildi.\n"
            f"{bot_bal_text}",
            reply_markup=build_admin_panel(),
        )
        return
    add_balance(uid, stars)
    set_step(uid, "home")
    bot.send_message(
        uid,
        f"{P('check')} To'lov qabul qilindi!\n\n"
        f"{P('star')} Hisobingizga {stars} {P('star')} qo'shildi.\n"
        f"{P('coin')} Jami balans: <b>{get_balance(uid)} {P('star')}</b>",
        reply_markup=menu_default(),
    )
    admin_id = get_setting("admin_id", "")
    if admin_id:
        try:
            bot.send_message(
                admin_id,
                f"{P('coin')} <b>Stars to'ldirildi</b>\n\n"
                f"Foydalanuvchi: {uid}\n"
                f"Miqdor: {stars} {P('star')}",
            )
        except Exception:
            pass


def start_keepalive():
    try:
        port = int(os.environ.get("PORT", "8080"))
    except (TypeError, ValueError):
        port = 8080
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import socketserver

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    class Server(socketserver.ThreadingMixIn, HTTPServer):
        daemon_threads = True

    try:
        server = Server(("0.0.0.0", port), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"HTTP keepalive {port} portda ishga tushdi")
    except Exception as e:
        print(f"HTTP keepalive ochilmadi: {e}")


def main():
    global BOT_USERNAME
    init_db()
    if os.environ.get("PORT"):
        start_keepalive()
    try:
        me = bot.get_me()
        BOT_USERNAME = me.username
        print(f"Bot ishga tushdi: @{BOT_USERNAME}")
    except Exception as e:
        print(f"get_me xatolik: {e}")
        BOT_USERNAME = "sizning_bot"
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"Polling xatolik: {e}; 5 soniyadan keyin qayta uriniladi")
            time.sleep(5)


if __name__ == "__main__":
    main()
