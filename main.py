import asyncio
import re
import random
import os
import threading
import sqlite3
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from flask import Flask

# =============== TOKENS & IDs ===============
API_ID = 30874435
API_HASH = "cc3b98786456de26fe5e803910051cea"
BOT_TOKEN = "8811228549:AAGsFA1_LhxrGg0MBb1fdN47tBj9q2VjK4E"
OWNER_ID = 8619852744
OWNER_USERNAME = "@Dwojj"

user_sessions = {}
active_spams = {}
user_steps = {}

DB_PATH = "subscriptions.db"

# =============== ملصقات مميزة فخمة جداً ===============
STICKERS = {
    "welcome": "CAACAgQAAxkBAAEB9MJlhG0AAWwVhCwFJjIAASjC2SujAAEKAg",      # ترحيب فخم
    "success": "CAACAgQAAxkBAAEB9NNlhG1-sZxZqWJfSvRgTl1RqPqZAg",      # نجاح فاخر
    "error": "CAACAgQAAxkBAAEB9NdjhG2O3Wj6qYzR7VrRqPqZAg",           # خطأ
    "loading": "CAACAgQAAxkBAAEB9NtlhG2kX0i7BkL1RqPqZAg",            # جاري التحميل
    "attack": "CAACAgQAAxkBAAEB9N9lhG25bRjTl1RqPqZAg",               # هجوم 🔥
    "luxury": "CAACAgQAAxkBAAEB9ONlhG3KbRjTl1RqPqZAg",               # فخم 👑
    "diamond": "CAACAgQAAxkBAAEB9OVlhG3RbRjTl1RqPqZAg",              # ماسة 💎
    "stop": "CAACAgQAAxkBAAEB9N9lhG25bRjTl1RqPqZAg",                 # إيقاف
    "login": "CAACAgQAAxkBAAEB9M9lhG1XWkKp0zL7xk7s8nR9qPqZAg",       # تسجيل دخول
    "gift": "CAACAgQAAxkBAAEB9ONlhG3KbRjTl1RqPqZAg",                 # هدية 🎁
    "warning": "CAACAgQAAxkBAAEB9NllhG2bVbR7jTl1RqPqZAg",            # تحذير ⚠️
    "rocket": "CAACAgQAAxkBAAEB9N1lhG2wYbRjTl1RqPqZAg",              # صاروخ 🚀
}

# =============== إيموجيات زخرفية فخمة ===============
EMOJI = {
    "fire": "🔥",
    "crown": "👑",
    "diamond": "💎",
    "star": "⭐",
    "rocket": "🚀",
    "warning": "⚠️",
    "success": "✅",
    "error": "❌",
    "loading": "⏳",
    "stop": "🛑",
    "login": "🔐",
    "gift": "🎁",
    "settings": "⚙️",
    "user": "👤",
    "users": "👥",
    "stats": "📊",
    "time": "⏰",
    "money": "💰",
    "lock": "🔒",
    "unlock": "🔓",
}

def get_sticker(sticker_key):
    """الحصول على ملصق عشوائي من المجموعة"""
    return STICKERS.get(sticker_key, STICKERS["luxury"])

async def send_fancy_message(chat_id, text, sticker_key=None, parse_mode="HTML"):
    """إرسال رسالة مع ملصق فخم"""
    if sticker_key:
        try:
            await bot.send_sticker(chat_id, get_sticker(sticker_key))
        except:
            pass
    await bot.send_message(chat_id, text, parse_mode=parse_mode)

async def send_fancy_reply(message, text, sticker_key=None, parse_mode="HTML"):
    """الرد على رسالة مع ملصق فخم"""
    if sticker_key:
        try:
            await bot.send_sticker(message.chat.id, get_sticker(sticker_key))
        except:
            pass
    await bot.reply_to(message, text, parse_mode=parse_mode)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (user_id TEXT PRIMARY KEY, expiry TEXT)''')
    conn.commit()
    conn.close()

def is_subscribed(user_id):
    user_id = str(user_id)
    if user_id == str(OWNER_ID):
        return True
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT expiry FROM subscriptions WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            expiry = datetime.fromisoformat(row[0])
            if datetime.now() < expiry:
                return True
            else:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
                conn.commit()
                conn.close()
        return False
    except Exception as e:
        print(f"DB Error: {e}")
        return False

def add_subscription(user_id, duration_hours):
    user_id = str(user_id)
    expiry = datetime.now() + timedelta(hours=duration_hours)
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)", (user_id, expiry.isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False

def get_subscription_time(user_id):
    user_id = str(user_id)
    if user_id == str(OWNER_ID):
        return "دائم"
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT expiry FROM subscriptions WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            expiry = datetime.fromisoformat(row[0])
            remaining = expiry - datetime.now()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            if hours > 0:
                return f"{hours}س {minutes}د"
            elif minutes > 0:
                return f"{minutes}د"
        return "غير مشترك"
    except Exception as e:
        return "خطأ"

def parse_duration(text):
    text = text.strip().lower()
    if text in ["نص ساعة", "نص ساعه"]:
        return 0.5
    match = re.match(r'(\d+(?:\.\d+)?)\s*(دقيقة|دقائق|د)', text)
    if match:
        return float(match.group(1)) / 60
    match = re.match(r'(\d+(?:\.\d+)?)\s*(ساعة|ساعات|س)', text)
    if match:
        return float(match.group(1))
    match = re.match(r'(\d+(?:\.\d+)?)\s*(يوم|أيام|ي)', text)
    if match:
        return float(match.group(1)) * 24
    return None

init_db()

# =============== جميع الكلمات القوية ===============
VERBS_POWER = [
    "لحلكك", "اشيلك", "عبالك", "انيجمك", "مصمص", "اهف", "اربطك", "اطحن", "اكهرب", "احط",
    "اقتحم", "اخدر", "انيج", "ربك", "اعبد", "ادحس", "افلش", "اذب", "اكعد", "ازورك", "اصعق",
]

NOUNS_POWER = [
    "الهالبك", "بعيري", "تيزمك", "علصدرك", "عيورتي", "بقياطين", "ضلوعك", "قضيبي", "نسلك",
    "زبي", "صريمك", "كسمك", "بكسختك", "براسك", "لكسمك", "بطيزك", "بكس امك", "بكسم اختك",
]

INSULTS_POWER = [
    "يا ابن الكلب", "يا ابن الشرموطه", "يا ابن القحبه", "يا ديوث", "يا خنيث", "يا ابن المتناكه",
    "يا ابن العاهره", "يا ابن الدعاره", "يا ابن الزانيه", "يا ابن الكحبه", "يا ابن العرص",
]

VERBS_EXTRA = [
    "كس امك", "كسمك", "كس اختك", "كسم امك", "كس عرضك", "كسم عرضك", "انيك امك", "انيك اختك",
    "انيك كس امك", "انيك كس اختك", "اطحن مخك", "افطر كبدك", "اشرب دمك", "اكل لحمك",
]

SAUDI_STRONG = [
    "يابنالقحبه", "شرموطه", "فحلمك", "يابن الزانيا", "انيكمك", "ركلمتك", "قذفتكمك",
    "خنيث", "ديوث", "قحبه", "عاهرة", "منيوك", "جرار", "سافل", "نذل", "حقير",
]

EXTRA_STRONG_WORDS = [
    "يابن المتناك", "يابن الزاني", "يابن الفاجر", "يابن الخاين", "يابن الحقير",
    "خنزير ابن خنزير", "كلب ابن كلب", "حمار ابن حمار",
]

TASTEER_STRONG = [
    "كس امك", "كسمك", "كس اختك", "كسم امك", "كس عرضك", "كسم عرضك", "انيك امك", "انيك اختك",
    "انيك كس امك", "انيك كس اختك", "اطحن مخك", "افطر كبدك",
]

MISC_STRONG = [
    "امك ديوثة", "اختك شرموطة", "خواتك كحبات", "نسلك منيوك", "عيلتك كلها زبالة",
]

ENDING_STRONG = [
    "وخر", "وانتهى", "والسلام", "والله لا يعود", "واخرتها معي",
]

NEW_STRONG_WORDS = [
    "يا ابن الكلب الأجرب", "يا ابن القحبة المنتنة", "يا شرموطة شارع",
]

def generate_millions_takleesh():
    parts = []
    parts.append(random.choice(VERBS_POWER))
    parts.append(random.choice(NOUNS_POWER))
    parts.append(random.choice(INSULTS_POWER))
    parts.append(random.choice(VERBS_EXTRA))
    parts.append(random.choice(SAUDI_STRONG))
    
    if random.random() > 0.3:
        parts.append(random.choice(INSULTS_POWER))
        parts.append(random.choice(SAUDI_STRONG))
        parts.append(random.choice(EXTRA_STRONG_WORDS))
    
    if random.random() > 0.5:
        parts.append("و")
        parts.append(random.choice(VERBS_EXTRA))
        parts.append(random.choice(SAUDI_STRONG))
        parts.append(random.choice(ENDING_STRONG))
    
    if random.random() > 0.7:
        parts.append(random.choice(MISC_STRONG))
        parts.append(random.choice(ENDING_STRONG))
    
    if random.random() > 0.8:
        parts.append(random.choice(NEW_STRONG_WORDS))
    
    return " ".join(parts)

def generate_millions_tasteer():
    patterns = [
        f"{random.choice(TASTEER_STRONG)} {random.choice(INSULTS_POWER)} {random.choice(SAUDI_STRONG)}",
        f"{random.choice(SAUDI_STRONG)} {random.choice(TASTEER_STRONG)} {random.choice(INSULTS_POWER)}",
        f"يا {random.choice(INSULTS_POWER)} يا {random.choice(SAUDI_STRONG)} يا {random.choice(TASTEER_STRONG)}",
        f"{random.choice(TASTEER_STRONG)} يا {random.choice(SAUDI_STRONG)} {random.choice(INSULTS_POWER)}",
        f"{random.choice(SAUDI_STRONG)} {random.choice(SAUDI_STRONG)} {random.choice(TASTEER_STRONG)}",
    ]
    return random.choice(patterns)

bot = AsyncTeleBot(BOT_TOKEN)

async def send_code_telethon(user_id, phone):
    try:
        client = TelegramClient(":memory:", API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            user_sessions[user_id] = {"client": client, "phone": phone, "step": "waiting_code"}
            return True
        else:
            user_sessions[user_id] = {"client": client, "phone": phone, "step": "ready"}
            return True
    except Exception as e:
        return str(e)

async def verify_code_telethon(user_id, code):
    data = user_sessions.get(user_id)
    if not data or data.get("step") != "waiting_code":
        return False
    client = data["client"]
    phone = data["phone"]
    try:
        await client.sign_in(phone, code=code)
        user_sessions[user_id]["step"] = "ready"
        return True
    except SessionPasswordNeededError:
        user_sessions[user_id]["step"] = "waiting_password"
        return "password_needed"
    except Exception as e:
        return str(e)

async def verify_password_telethon(user_id, password):
    data = user_sessions.get(user_id)
    if not data or data.get("step") != "waiting_password":
        return False
    client = data["client"]
    try:
        await client.sign_in(password=password)
        user_sessions[user_id]["step"] = "ready"
        return True
    except Exception as e:
        return str(e)

def is_verified(user_id):
    return user_id in user_sessions and user_sessions[user_id].get("step") == "ready"

def get_client(user_id):
    return user_sessions.get(user_id, {}).get("client")

async def send_takleesh_messages(user_id, target, count, chat_id):
    if not is_subscribed(user_id):
        await send_fancy_message(chat_id, f"{EMOJI['error']} اشتراك مطلوب: /subscribe", "error")
        return
    if user_id in active_spams:
        active_spams[user_id]["stop"] = False
    else:
        active_spams[user_id] = {"stop": False}
    client = get_client(user_id)
    if not client:
        await send_fancy_message(chat_id, f"{EMOJI['error']} خطأ في الجلسة", "error")
        return
    
    for i in range(count):
        if active_spams[user_id]["stop"]:
            await send_fancy_message(chat_id, f"{EMOJI['stop']} تم الإيقاف", "stop")
            break
        word = generate_millions_takleesh()
        try:
            await client.send_message(target, word)
            await send_fancy_message(chat_id, f"{EMOJI['success']} [{i+1}/{count}] تم الارسال", "success")
        except Exception as e:
            await send_fancy_message(chat_id, f"{EMOJI['error']} فشل: {str(e)}", "error")
            break
        await asyncio.sleep(3)
    
    await send_fancy_message(chat_id, f"{EMOJI['success']} تم إرسال {count} كليشة", "success")
    if user_id in active_spams:
        del active_spams[user_id]

async def send_tasteer_messages(user_id, target, lines, chat_id):
    if not is_subscribed(user_id):
        await send_fancy_message(chat_id, f"{EMOJI['error']} اشتراك مطلوب: /subscribe", "error")
        return
    if user_id in active_spams:
        active_spams[user_id]["stop"] = False
    else:
        active_spams[user_id] = {"stop": False}
    client = get_client(user_id)
    if not client:
        await send_fancy_message(chat_id, f"{EMOJI['error']} خطأ في الجلسة", "error")
        return
    
    for i in range(lines):
        if active_spams[user_id]["stop"]:
            await send_fancy_message(chat_id, f"{EMOJI['stop']} تم الإيقاف", "stop")
            break
        word = generate_millions_tasteer()
        try:
            await client.send_message(target, word)
            await send_fancy_message(chat_id, f"{EMOJI['success']} [{i+1}/{lines}] تم الارسال", "success")
        except Exception as e:
            await send_fancy_message(chat_id, f"{EMOJI['error']} فشل: {str(e)}", "error")
            break
        await asyncio.sleep(3)
    
    await send_fancy_message(chat_id, f"{EMOJI['success']} تم إرسال {lines} سطر", "success")
    if user_id in active_spams:
        del active_spams[user_id]

# =============== واجهة ترحيب فخمة جداً ===============
@bot.message_handler(commands=['start'])
async def start(message):
    status = get_subscription_time(message.from_user.id)
    name = message.from_user.first_name or "صديقي"
    
    # إرسال ملصق ترحيب فخم أولاً
    await bot.send_sticker(message.chat.id, STICKERS["welcome"])
    
    caption = f"""
{EMOJI['crown']}━━━━━━━━━━━━━━━━━━━━{EMOJI['crown']}
{EMOJI['fire']} <b>TNT SHADOW BOT</b> {EMOJI['fire']}
{EMOJI['crown']}━━━━━━━━━━━━━━━━━━━━{EMOJI['crown']}

{EMOJI['star']} <b>مرحباً {name}</b> {EMOJI['star']}
{EMOJI['diamond']} <b>الاشتراك</b> : {status}

{EMOJI['crown']}━━━━━━━━━━━━━━━━━━━━{EMOJI['crown']}
{EMOJI['rocket']} <b>الأوامر المتاحة</b> {EMOJI['rocket']}
{EMOJI['crown']}━━━━━━━━━━━━━━━━━━━━{EMOJI['crown']}

{EMOJI['login']} <code>/login</code> → تسجيل دخول
{EMOJI['fire']} <code>/takleesh</code> → هجوم تكليش
{EMOJI['settings']} <code>/tasteer</code> → هجوم تسطير
{EMOJI['stop']} <code>/stop</code> → إيقاف الهجوم
{EMOJI['gift']} <code>/subscribe</code> → اشتراك مميز
{EMOJI['time']} <code>/myplan</code> → متبقي من الاشتراك

{EMOJI['crown']}━━━━━━━━━━━━━━━━━━━━{EMOJI['crown']}
{EMOJI['crown']} <b>المطور</b> : {OWNER_USERNAME} {EMOJI['crown']}
{EMOJI['crown']}━━━━━━━━━━━━━━━━━━━━{EMOJI['crown']}
"""
    await bot.send_photo(message.chat.id, "https://l.top4top.io/p_3804s3rqj0.jpg", caption=caption, parse_mode="HTML")

@bot.message_handler(commands=['subscribe'])
async def subscribe(message):
    await bot.send_sticker(message.chat.id, STICKERS["gift"])
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(f"{EMOJI['star']} ساعة - 15 {EMOJI['star']}", callback_data="sub_hour"),
        InlineKeyboardButton(f"{EMOJI['diamond']} يوم - 50 {EMOJI['diamond']}", callback_data="sub_day"),
        InlineKeyboardButton(f"{EMOJI['crown']} اسبوع - 150 {EMOJI['crown']}", callback_data="sub_week"),
        InlineKeyboardButton(f"{EMOJI['fire']} شهر - 250 {EMOJI['fire']}", callback_data="sub_month")
    )
    await bot.reply_to(message, f"{EMOJI['gift']} <b>اختر مدة الاشتراك</b> {EMOJI['gift']}", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
async def handle_subscription(call):
    plans = {
        "sub_hour": {"stars": 15, "hours": 1, "name": "ساعة", "price": 15},
        "sub_day": {"stars": 50, "hours": 24, "name": "يوم", "price": 50},
        "sub_week": {"stars": 150, "hours": 168, "name": "اسبوع", "price": 150},
        "sub_month": {"stars": 250, "hours": 720, "name": "شهر", "price": 250}
    }
    plan = plans.get(call.data)
    if plan:
        await bot.answer_callback_query(call.id)
        prices = [LabeledPrice(label=f"⭐ {plan['name']}", amount=plan['price'])]
        await bot.send_invoice(
            chat_id=call.message.chat.id,
            title=f"اشتراك {plan['name']}",
            description=f"{EMOJI['star']} {plan['stars']} نجمة - {plan['name']} {EMOJI['star']}",
            invoice_payload=f"sub_{plan['name']}",
            provider_token="",
            currency="XTR",
            prices=prices
        )

@bot.pre_checkout_query_handler(func=lambda query: True)
async def checkout(pre_checkout_query):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
async def successful_payment(message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    await bot.send_sticker(message.chat.id, STICKERS["success"])
    if "ساعة" in payload:
        add_subscription(user_id, 1)
        await bot.reply_to(message, f"{EMOJI['success']} تم تفعيل اشتراكك لمدة ساعة {EMOJI['success']}")
    elif "يوم" in payload:
        add_subscription(user_id, 24)
        await bot.reply_to(message, f"{EMOJI['success']} تم تفعيل اشتراكك لمدة يوم {EMOJI['success']}")
    elif "اسبوع" in payload:
        add_subscription(user_id, 168)
        await bot.reply_to(message, f"{EMOJI['success']} تم تفعيل اشتراكك لمدة اسبوع {EMOJI['success']}")
    elif "شهر" in payload:
        add_subscription(user_id, 720)
        await bot.reply_to(message, f"{EMOJI['success']} تم تفعيل اشتراكك لمدة شهر {EMOJI['success']}")

@bot.message_handler(commands=['myplan'])
async def myplan(message):
    await bot.send_sticker(message.chat.id, STICKERS["diamond"])
    await bot.reply_to(message, f"{EMOJI['diamond']} حالتك: {get_subscription_time(message.from_user.id)} {EMOJI['diamond']}")

@bot.message_handler(commands=['gift'])
async def gift_subscription(message):
    if message.from_user.id != OWNER_ID:
        await send_fancy_reply(message, f"{EMOJI['error']} للأونر فقط", "error")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await send_fancy_reply(message, f"{EMOJI['warning']} /gift [ايدي] [مدة]\nمثال: /gift 8619852744 5 دقائق", "warning")
        return
    try:
        target_id = int(args[1])
        hours = parse_duration(args[2])
        if hours:
            add_subscription(target_id, hours)
            await send_fancy_reply(message, f"{EMOJI['success']} تم تفعيل اشتراك {target_id}", "success")
            try:
                await bot.send_sticker(target_id, STICKERS["gift"])
                await bot.send_message(target_id, f"{EMOJI['gift']} تم تفعيل اشتراك لك لمدة {args[2]} بواسطة الأونر {OWNER_USERNAME} {EMOJI['gift']}")
            except:
                pass
    except:
        await send_fancy_reply(message, f"{EMOJI['error']} خطأ في البيانات", "error")

@bot.message_handler(commands=['login'])
async def login(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await send_fancy_reply(message, f"{EMOJI['error']} اشتراك مطلوب: /subscribe", "error")
        return
    if is_verified(user_id):
        await send_fancy_reply(message, f"{EMOJI['success']} مسجل بالفعل", "success")
        return
    user_steps[user_id] = {"step": "waiting_phone"}
    await bot.send_sticker(message.chat.id, STICKERS["login"])
    await bot.reply_to(message, f"{EMOJI['login']} <b>ارسل رقمك مع +</b>\nمثال: +966512345678", parse_mode="HTML")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_phone")
async def handle_phone(message):
    user_id = message.from_user.id
    phone = message.text.strip()
    if not phone.startswith('+'):
        await send_fancy_reply(message, f"{EMOJI['error']} الرقم يبدأ بـ +", "error")
        return
    await bot.send_sticker(message.chat.id, STICKERS["loading"])
    await bot.reply_to(message, f"{EMOJI['loading']} جاري ارسال الكود...")
    result = await send_code_telethon(user_id, phone)
    if result is True:
        user_steps[user_id] = {"step": "waiting_code"}
        await send_fancy_reply(message, f"{EMOJI['success']} تم ارسال الكود\nادخل الكود بارقام فقط:\nمثال: 12345", "success")
    else:
        await send_fancy_reply(message, f"{EMOJI['error']} فشل: {result}", "error")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_code")
async def handle_code(message):
    user_id = message.from_user.id
    code = message.text.strip().replace(" ", "")
    if not code.isdigit():
        await send_fancy_reply(message, f"{EMOJI['error']} الكود ارقام فقط", "error")
        return
    result = await verify_code_telethon(user_id, code)
    if result is True:
        del user_steps[user_id]
        await bot.send_sticker(message.chat.id, STICKERS["success"])
        await bot.reply_to(message, f"{EMOJI['success']} تم الدخول\n{EMOJI['fire']} /takleesh\n{EMOJI['settings']} /tasteer")
    elif result == "password_needed":
        user_steps[user_id] = {"step": "waiting_password"}
        await send_fancy_reply(message, f"{EMOJI['lock']} ارسل كلمة المرور:", "login")
    else:
        await send_fancy_reply(message, f"{EMOJI['error']} كود خطأ", "error")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_password")
async def handle_password(message):
    user_id = message.from_user.id
    password = message.text.strip()
    result = await verify_password_telethon(user_id, password)
    if result is True:
        del user_steps[user_id]
        await bot.send_sticker(message.chat.id, STICKERS["success"])
        await bot.reply_to(message, f"{EMOJI['success']} تم الدخول")
    else:
        await send_fancy_reply(message, f"{EMOJI['error']} كلمة مرور خطأ", "error")
        del user_steps[user_id]

@bot.message_handler(commands=['takleesh'])
async def takleesh(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await send_fancy_reply(message, f"{EMOJI['error']} اشتراك مطلوب: /subscribe", "error")
        return
    if not is_verified(user_id):
        await send_fancy_reply(message, f"{EMOJI['error']} سجل دخول: /login", "error")
        return
    if user_id in active_spams:
        await send_fancy_reply(message, f"{EMOJI['warning']} عملية شغالة: /stop", "warning")
        return
    user_steps[user_id] = {"step": "takleesh_target"}
    await bot.send_sticker(message.chat.id, STICKERS["attack"])
    await bot.reply_to(message, f"{EMOJI['target']} <b>ارسل معرف المستهدف</b> (@username او ID):", parse_mode="HTML")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_target")
async def takleesh_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "takleesh_count", "target": target}
    await bot.reply_to(message, f"{EMOJI['stats']} <b>عدد الرسائل:</b>", parse_mode="HTML")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_count")
async def takleesh_count(message):
    user_id = message.from_user.id
    try:
        count = int(message.text.strip())
        if count < 1:
            raise ValueError
    except:
        await send_fancy_reply(message, f"{EMOJI['error']} عدد غير صالح", "error")
        del user_steps[user_id]
        return
    target = user_steps[user_id]["target"]
    await bot.send_sticker(message.chat.id, STICKERS["rocket"])
    await bot.reply_to(message, f"{EMOJI['rocket']} جاري ارسال {count} كليشة (3 ثواني بين كل كليشة)")
    asyncio.create_task(send_takleesh_messages(user_id, target, count, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['tasteer'])
async def tasteer(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await send_fancy_reply(message, f"{EMOJI['error']} اشتراك مطلوب: /subscribe", "error")
        return
    if not is_verified(user_id):
        await send_fancy_reply(message, f"{EMOJI['error']} سجل دخول: /login", "error")
        return
    if user_id in active_spams:
        await send_fancy_reply(message, f"{EMOJI['warning']} عملية شغالة: /stop", "warning")
        return
    user_steps[user_id] = {"step": "tasteer_target"}
    await bot.send_sticker(message.chat.id, STICKERS["attack"])
    await bot.reply_to(message, f"{EMOJI['target']} <b>ارسل معرف المستهدف</b> (@username او ID):", parse_mode="HTML")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_target")
async def tasteer_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "tasteer_lines", "target": target}
    await bot.reply_to(message, f"{EMOJI['stats']} <b>عدد الاسطر:</b>", parse_mode="HTML")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_lines")
async def tasteer_lines(message):
    user_id = message.from_user.id
    try:
        lines = int(message.text.strip())
        if lines < 1:
            raise ValueError
    except:
        await send_fancy_reply(message, f"{EMOJI['error']} عدد غير صالح", "error")
        del user_steps[user_id]
        return
    target = user_steps[user_id]["target"]
    await bot.send_sticker(message.chat.id, STICKERS["rocket"])
    await bot.reply_to(message, f"{EMOJI['rocket']} جاري ارسال {lines} سطر (3 ثواني بين كل سطر)")
    asyncio.create_task(send_tasteer_messages(user_id, target, lines, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['stop'])
async def stop(message):
    user_id = message.from_user.id
    if user_id in active_spams:
        active_spams[user_id]["stop"] = True
        await bot.send_sticker(message.chat.id, STICKERS["stop"])
        await bot.reply_to(message, f"{EMOJI['stop']} تم الايقاف")
    else:
        await send_fancy_reply(message, f"{EMOJI['warning']} لا توجد عملية", "warning")

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🔥 TNT SHADOW BOT - التشغيل ممتاز 🔥"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

async def main():
    print(f"{EMOJI['fire']}{EMOJI['crown']}{EMOJI['diamond']} TNT SHADOW BOT is running... {EMOJI['diamond']}{EMOJI['crown']}{EMOJI['fire']}")
    print(f"{EMOJI['success']} 3 ثواني بين كل رسالة")
    print(f"{EMOJI['success']} مشكلة قاعدة البيانات تم حلها")
    print(f"{EMOJI['star']} تم إضافة ملصقات فخمة في كل مكان!")
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
