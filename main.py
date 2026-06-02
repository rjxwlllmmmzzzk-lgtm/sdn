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

# =============== إيموجيات تيليجرام الأصلية (المميزة) ===============
CE = {
    '✅': '<tg-emoji emoji-id="6258259403200270844">✅</tg-emoji>',
    '❌': '<tg-emoji emoji-id="5796291784539639311">❌</tg-emoji>',
    '⚠️': '<tg-emoji emoji-id="5999278377104578246">⚠️</tg-emoji>',
    '🔥': '<tg-emoji emoji-id="5976831692604709621">🔥</tg-emoji>',
    '👑': '<tg-emoji emoji-id="5319149831673887746">👑</tg-emoji>',
    '💎': '<tg-emoji emoji-id="5254001839287859496">💎</tg-emoji>',
    '⭐': '<tg-emoji emoji-id="5254001839287859496">⭐</tg-emoji>',
    '🚀': '<tg-emoji emoji-id="5967301267549068409">🚀</tg-emoji>',
    '🎯': '<tg-emoji emoji-id="5965466792527666087">🎯</tg-emoji>',
    '🔐': '<tg-emoji emoji-id="5785167918027250397">🔐</tg-emoji>',
    '🔒': '<tg-emoji emoji-id="5785167918027250397">🔒</tg-emoji>',
    '🎁': '<tg-emoji emoji-id="5976317950091598658">🎁</tg-emoji>',
    '⏰': '<tg-emoji emoji-id="5314299563761222650">⏰</tg-emoji>',
    '⏳': '<tg-emoji emoji-id="5314299563761222650">⏳</tg-emoji>',
    '🛑': '<tg-emoji emoji-id="5888789252493283486">🛑</tg-emoji>',
    '📊': '<tg-emoji emoji-id="5935935761336505948">📊</tg-emoji>',
    '👤': '<tg-emoji emoji-id="5373020661574826232">👤</tg-emoji>',
    '⚙️': '<tg-emoji emoji-id="5857054220179480029">⚙️</tg-emoji>',
    '💬': '<tg-emoji emoji-id="5314299563761222650">💬</tg-emoji>',
    '📱': '<tg-emoji emoji-id="5834628314731387616">📱</tg-emoji>',
    '💰': '<tg-emoji emoji-id="6037182124916740433">💰</tg-emoji>',
    '✨': '<tg-emoji emoji-id="5254001839287859496">✨</tg-emoji>',
    '🎉': '<tg-emoji emoji-id="5254001839287859496">🎉</tg-emoji>',
    '🔍': '<tg-emoji emoji-id="5965466792527666087">🔍</tg-emoji>',
    '📢': '<tg-emoji emoji-id="5902385465390013835">📢</tg-emoji>',
    '💗': '<tg-emoji emoji-id="6043941205144771802">💗</tg-emoji>',
    '🤖': '<tg-emoji emoji-id="5254001839287859496">🤖</tg-emoji>',
}

def ce(text):
    """تحويل النص إلى إيموجيات تيليجرام مميزة"""
    if not text:
        return text
    for ch, replacement in CE.items():
        text = text.replace(ch, replacement)
    return text

def bq(text):
    """إضافة blockquote مع إيموجيات مميزة"""
    return f"<blockquote>{ce(str(text))}</blockquote>"

# =============== ملصقات مميزة فخمة جداً ===============
STICKERS = {
    "welcome": "CAACAgQAAxkBAAEB9MJlhG0AAWwVhCwFJjIAASjC2SujAAEKAg",
    "success": "CAACAgQAAxkBAAEB9NNlhG1-sZxZqWJfSvRgTl1RqPqZAg",
    "error": "CAACAgQAAxkBAAEB9NdjhG2O3Wj6qYzR7VrRqPqZAg",
    "loading": "CAACAgQAAxkBAAEB9NtlhG2kX0i7BkL1RqPqZAg",
    "attack": "CAACAgQAAxkBAAEB9N9lhG25bRjTl1RqPqZAg",
    "luxury": "CAACAgQAAxkBAAEB9ONlhG3KbRjTl1RqPqZAg",
    "diamond": "CAACAgQAAxkBAAEB9OVlhG3RbRjTl1RqPqZAg",
    "stop": "CAACAgQAAxkBAAEB9N9lhG25bRjTl1RqPqZAg",
    "login": "CAACAgQAAxkBAAEB9M9lhG1XWkKp0zL7xk7s8nR9qPqZAg",
    "gift": "CAACAgQAAxkBAAEB9ONlhG3KbRjTl1RqPqZAg",
    "warning": "CAACAgQAAxkBAAEB9NllhG2bVbR7jTl1RqPqZAg",
    "rocket": "CAACAgQAAxkBAAEB9N1lhG2wYbRjTl1RqPqZAg",
}

def get_sticker(sticker_key):
    return STICKERS.get(sticker_key, STICKERS["luxury"])

async def send_fancy_message(chat_id, text, sticker_key=None, parse_mode="HTML"):
    if sticker_key:
        try:
            await bot.send_sticker(chat_id, get_sticker(sticker_key))
        except:
            pass
    await bot.send_message(chat_id, bq(text), parse_mode=parse_mode)

async def send_fancy_reply(message, text, sticker_key=None, parse_mode="HTML"):
    if sticker_key:
        try:
            await bot.send_sticker(message.chat.id, get_sticker(sticker_key))
        except:
            pass
    await bot.reply_to(message, bq(text), parse_mode=parse_mode)

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
        return f"{CE['👑']} دائم {CE['👑']}"
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
                return f"{hours}س {minutes}د {CE['⏰']}"
            elif minutes > 0:
                return f"{minutes}د {CE['⏰']}"
        return f"{CE['❌']} غير مشترك {CE['❌']}"
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

# =============== كلمات الهجوم ===============
VERBS_POWER = ["لحلكك", "اشيلك", "عبالك", "انيجمك", "مصمص", "اهف", "اربطك", "اطحن"]
NOUNS_POWER = ["الهالبك", "بعيري", "تيزمك", "علصدرك", "قضيبي", "زبي", "كسمك"]
INSULTS_POWER = ["يا ابن الكلب", "يا ابن الشرموطه", "يا ديوث", "يا خنيث"]
VERBS_EXTRA = ["كس امك", "كسمك", "انيك امك", "اطحن مخك"]
SAUDI_STRONG = ["يابنالقحبه", "شرموطه", "خنيث", "ديوث", "قحبه"]
TASTEER_STRONG = ["كس امك", "كسمك", "انيك امك", "اطحن مخك"]

def generate_millions_takleesh():
    parts = [random.choice(VERBS_POWER), random.choice(NOUNS_POWER), random.choice(INSULTS_POWER), random.choice(VERBS_EXTRA), random.choice(SAUDI_STRONG)]
    return " ".join(parts)

def generate_millions_tasteer():
    return random.choice([f"{random.choice(TASTEER_STRONG)} {random.choice(INSULTS_POWER)}", f"{random.choice(SAUDI_STRONG)} {random.choice(TASTEER_STRONG)}"])

bot = AsyncTeleBot(BOT_TOKEN, parse_mode="HTML")

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
        await send_fancy_message(chat_id, f"{CE['❌']} اشتراك مطلوب: /subscribe {CE['❌']}", "error")
        return
    if user_id in active_spams:
        active_spams[user_id]["stop"] = False
    else:
        active_spams[user_id] = {"stop": False}
    client = get_client(user_id)
    if not client:
        await send_fancy_message(chat_id, f"{CE['❌']} خطأ في الجلسة {CE['❌']}", "error")
        return
    for i in range(count):
        if active_spams[user_id]["stop"]:
            await send_fancy_message(chat_id, f"{CE['🛑']} تم الإيقاف {CE['🛑']}", "stop")
            break
        word = generate_millions_takleesh()
        try:
            await client.send_message(target, word)
            await send_fancy_message(chat_id, f"{CE['✅']} [{i+1}/{count}] تم الارسال {CE['✅']}", "success")
        except Exception as e:
            await send_fancy_message(chat_id, f"{CE['❌']} فشل: {str(e)} {CE['❌']}", "error")
            break
        await asyncio.sleep(3)
    await send_fancy_message(chat_id, f"{CE['✅']} تم إرسال {count} كليشة {CE['✅']}", "success")
    if user_id in active_spams:
        del active_spams[user_id]

async def send_tasteer_messages(user_id, target, lines, chat_id):
    if not is_subscribed(user_id):
        await send_fancy_message(chat_id, f"{CE['❌']} اشتراك مطلوب: /subscribe {CE['❌']}", "error")
        return
    if user_id in active_spams:
        active_spams[user_id]["stop"] = False
    else:
        active_spams[user_id] = {"stop": False}
    client = get_client(user_id)
    if not client:
        await send_fancy_message(chat_id, f"{CE['❌']} خطأ في الجلسة {CE['❌']}", "error")
        return
    for i in range(lines):
        if active_spams[user_id]["stop"]:
            await send_fancy_message(chat_id, f"{CE['🛑']} تم الإيقاف {CE['🛑']}", "stop")
            break
        word = generate_millions_tasteer()
        try:
            await client.send_message(target, word)
            await send_fancy_message(chat_id, f"{CE['✅']} [{i+1}/{lines}] تم الارسال {CE['✅']}", "success")
        except Exception as e:
            await send_fancy_message(chat_id, f"{CE['❌']} فشل: {str(e)} {CE['❌']}", "error")
            break
        await asyncio.sleep(3)
    await send_fancy_message(chat_id, f"{CE['✅']} تم إرسال {lines} سطر {CE['✅']}", "success")
    if user_id in active_spams:
        del active_spams[user_id]

# =============== أوامر البوت مع إيموجيات مميزة ===============
@bot.message_handler(commands=['start'])
async def start(message):
    status = get_subscription_time(message.from_user.id)
    name = message.from_user.first_name or "صديقي"
    
    try:
        await bot.send_sticker(message.chat.id, STICKERS["welcome"])
    except:
        pass
    
    caption = f"""
{CE['👑']}━━━━━━━━━━━━━━━━━━━━{CE['👑']}
{CE['🔥']} <b>TNT SHADOW BOT</b> {CE['🔥']}
{CE['👑']}━━━━━━━━━━━━━━━━━━━━{CE['👑']}

{CE['⭐']} <b>مرحباً {name}</b> {CE['⭐']}
{CE['💎']} <b>الاشتراك</b> : {status}

{CE['👑']}━━━━━━━━━━━━━━━━━━━━{CE['👑']}
{CE['🚀']} <b>الأوامر المتاحة</b> {CE['🚀']}
{CE['👑']}━━━━━━━━━━━━━━━━━━━━{CE['👑']}

{CE['🔐']} <code>/login</code> → تسجيل دخول
{CE['🔥']} <code>/takleesh</code> → هجوم تكليش
{CE['⚙️']} <code>/tasteer</code> → هجوم تسطير
{CE['🛑']} <code>/stop</code> → إيقاف الهجوم
{CE['🎁']} <code>/subscribe</code> → اشتراك مميز
{CE['⏰']} <code>/myplan</code> → متبقي من الاشتراك

{CE['👑']}━━━━━━━━━━━━━━━━━━━━{CE['👑']}
{CE['👑']} <b>المطور</b> : {OWNER_USERNAME} {CE['👑']}
{CE['👑']}━━━━━━━━━━━━━━━━━━━━{CE['👑']}
"""
    try:
        await bot.send_photo(message.chat.id, "https://l.top4top.io/p_3804s3rqj0.jpg", caption=caption, parse_mode="HTML")
    except:
        await bot.send_message(message.chat.id, caption, parse_mode="HTML")

@bot.message_handler(commands=['subscribe'])
async def subscribe(message):
    try:
        await bot.send_sticker(message.chat.id, STICKERS["gift"])
    except:
        pass
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(f"{CE['⭐']} ساعة - 15 {CE['⭐']}", callback_data="sub_hour"),
        InlineKeyboardButton(f"{CE['💎']} يوم - 50 {CE['💎']}", callback_data="sub_day"),
        InlineKeyboardButton(f"{CE['👑']} اسبوع - 150 {CE['👑']}", callback_data="sub_week"),
        InlineKeyboardButton(f"{CE['🔥']} شهر - 250 {CE['🔥']}", callback_data="sub_month")
    )
    await bot.reply_to(message, f"{CE['🎁']} <b>اختر مدة الاشتراك</b> {CE['🎁']}", reply_markup=markup, parse_mode="HTML")

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
            description=f"{CE['⭐']} {plan['stars']} نجمة - {plan['name']} {CE['⭐']}",
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
    try:
        await bot.send_sticker(message.chat.id, STICKERS["success"])
    except:
        pass
    if "ساعة" in payload:
        add_subscription(user_id, 1)
        await bot.reply_to(message, f"{CE['✅']} تم تفعيل اشتراكك لمدة ساعة {CE['✅']}")
    elif "يوم" in payload:
        add_subscription(user_id, 24)
        await bot.reply_to(message, f"{CE['✅']} تم تفعيل اشتراكك لمدة يوم {CE['✅']}")
    elif "اسبوع" in payload:
        add_subscription(user_id, 168)
        await bot.reply_to(message, f"{CE['✅']} تم تفعيل اشتراكك لمدة اسبوع {CE['✅']}")
    elif "شهر" in payload:
        add_subscription(user_id, 720)
        await bot.reply_to(message, f"{CE['✅']} تم تفعيل اشتراكك لمدة شهر {CE['✅']}")

@bot.message_handler(commands=['myplan'])
async def myplan(message):
    try:
        await bot.send_sticker(message.chat.id, STICKERS["diamond"])
    except:
        pass
    await bot.reply_to(message, f"{CE['💎']} حالتك: {get_subscription_time(message.from_user.id)} {CE['💎']}")

@bot.message_handler(commands=['gift'])
async def gift_subscription(message):
    if message.from_user.id != OWNER_ID:
        await send_fancy_reply(message, f"{CE['❌']} للأونر فقط {CE['❌']}", "error")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await send_fancy_reply(message, f"{CE['⚠️']} /gift [ايدي] [مدة]{CE['⚠️']}\nمثال: /gift 8619852744 5 دقائق", "warning")
        return
    try:
        target_id = int(args[1])
        hours = parse_duration(args[2])
        if hours:
            add_subscription(target_id, hours)
            await send_fancy_reply(message, f"{CE['✅']} تم تفعيل اشتراك {target_id} {CE['✅']}", "success")
            try:
                await bot.send_sticker(target_id, STICKERS["gift"])
                await bot.send_message(target_id, f"{CE['🎁']} تم تفعيل اشتراك لك لمدة {args[2]} بواسطة الأونر {OWNER_USERNAME} {CE['🎁']}")
            except:
                pass
    except:
        await send_fancy_reply(message, f"{CE['❌']} خطأ في البيانات {CE['❌']}", "error")

@bot.message_handler(commands=['login'])
async def login(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await send_fancy_reply(message, f"{CE['❌']} اشتراك مطلوب: /subscribe {CE['❌']}", "error")
        return
    if is_verified(user_id):
        await send_fancy_reply(message, f"{CE['✅']} مسجل بالفعل {CE['✅']}", "success")
        return
    user_steps[user_id] = {"step": "waiting_phone"}
    try:
        await bot.send_sticker(message.chat.id, STICKERS["login"])
    except:
        pass
    await bot.reply_to(message, f"{CE['🔐']} <b>ارسل رقمك مع +</b>{CE['🔐']}\nمثال: +966512345678", parse_mode="HTML")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_phone")
async def handle_phone(message):
    user_id = message.from_user.id
    phone = message.text.strip()
    if not phone.startswith('+'):
        await send_fancy_reply(message, f"{CE['❌']} الرقم يبدأ بـ + {CE['❌']}", "error")
        return
    try:
        await bot.send_sticker(message.chat.id, STICKERS["loading"])
    except:
        pass
    await bot.reply_to(message, f"{CE['⏳']} جاري ارسال الكود... {CE['⏳']}")
    result = await send_code_telethon(user_id, phone)
    if result is True:
        user_steps[user_id] = {"step": "waiting_code"}
        await send_fancy_reply(message, f"{CE['✅']} تم ارسال الكود {CE['✅']}\nادخل الكود بارقام فقط:", "success")
    else:
        await send_fancy_reply(message, f"{CE['❌']} فشل: {result} {CE['❌']}", "error")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_code")
async def handle_code(message):
    user_id = message.from_user.id
    code = message.text.strip().replace(" ", "")
    if not code.isdigit():
        await send_fancy_reply(message, f"{CE['❌']} الكود ارقام فقط {CE['❌']}", "error")
        return
    result = await verify_code_telethon(user_id, code)
    if result is True:
        del user_steps[user_id]
        try:
            await bot.send_sticker(message.chat.id, STICKERS["success"])
        except:
            pass
        await bot.reply_to(message, f"{CE['✅']} تم الدخول {CE['✅']}\n{CE['🔥']} /takleesh\n{CE['⚙️']} /tasteer")
    elif result == "password_needed":
        user_steps[user_id] = {"step": "waiting_password"}
        await send_fancy_reply(message, f"{CE['🔒']} ارسل كلمة المرور: {CE['🔒']}", "login")
    else:
        await send_fancy_reply(message, f"{CE['❌']} كود خطأ {CE['❌']}", "error")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_password")
async def handle_password(message):
    user_id = message.from_user.id
    password = message.text.strip()
    result = await verify_password_telethon(user_id, password)
    if result is True:
        del user_steps[user_id]
        try:
            await bot.send_sticker(message.chat.id, STICKERS["success"])
        except:
            pass
        await bot.reply_to(message, f"{CE['✅']} تم الدخول {CE['✅']}")
    else:
        await send_fancy_reply(message, f"{CE['❌']} كلمة مرور خطأ {CE['❌']}", "error")
        del user_steps[user_id]

@bot.message_handler(commands=['takleesh'])
async def takleesh(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await send_fancy_reply(message, f"{CE['❌']} اشتراك مطلوب: /subscribe {CE['❌']}", "error")
        return
    if not is_verified(user_id):
        await send_fancy_reply(message, f"{CE['❌']} سجل دخول: /login {CE['❌']}", "error")
        return
    if user_id in active_spams:
        await send_fancy_reply(message, f"{CE['⚠️']} عملية شغالة: /stop {CE['⚠️']}", "warning")
        return
    user_steps[user_id] = {"step": "takleesh_target"}
    try:
        await bot.send_sticker(message.chat.id, STICKERS["attack"])
    except:
        pass
    await bot.reply_to(message, f"{CE['🎯']} <b>ارسل معرف المستهدف</b> (@username او ID): {CE['🎯']}", parse_mode="HTML")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_target")
async def takleesh_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "takleesh_count", "target": target}
    await bot.reply_to(message, f"{CE['📊']} <b>عدد الرسائل:</b> {CE['📊']}", parse_mode="HTML")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_count")
async def takleesh_count(message):
    user_id = message.from_user.id
    try:
        count = int(message.text.strip())
        if count < 1:
            raise ValueError
    except:
        await send_fancy_reply(message, f"{CE['❌']} عدد غير صالح {CE['❌']}", "error")
        del user_steps[user_id]
        return
    target = user_steps[user_id]["target"]
    try:
        await bot.send_sticker(message.chat.id, STICKERS["rocket"])
    except:
        pass
    await bot.reply_to(message, f"{CE['🚀']} جاري ارسال {count} كليشة {CE['🚀']}")
    asyncio.create_task(send_takleesh_messages(user_id, target, count, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['tasteer'])
async def tasteer(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await send_fancy_reply(message, f"{CE['❌']} اشتراك مطلوب: /subscribe {CE['❌']}", "error")
        return
    if not is_verified(user_id):
        await send_fancy_reply(message, f"{CE['❌']} سجل دخول: /login {CE['❌']}", "error")
        return
    if user_id in active_spams:
        await send_fancy_reply(message, f"{CE['⚠️']} عملية شغالة: /stop {CE['⚠️']}", "warning")
        return
    user_steps[user_id] = {"step": "tasteer_target"}
    try:
        await bot.send_sticker(message.chat.id, STICKERS["attack"])
    except:
        pass
    await bot.reply_to(message, f"{CE['🎯']} <b>ارسل معرف المستهدف</b> (@username او ID): {CE['🎯']}", parse_mode="HTML")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_target")
async def tasteer_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "tasteer_lines", "target": target}
    await bot.reply_to(message, f"{CE['📊']} <b>عدد الاسطر:</b> {CE['📊']}", parse_mode="HTML")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_lines")
async def tasteer_lines(message):
    user_id = message.from_user.id
    try:
        lines = int(message.text.strip())
        if lines < 1:
            raise ValueError
    except:
        await send_fancy_reply(message, f"{CE['❌']} عدد غير صالح {CE['❌']}", "error")
        del user_steps[user_id]
        return
    target = user_steps[user_id]["target"]
    try:
        await bot.send_sticker(message.chat.id, STICKERS["rocket"])
    except:
        pass
    await bot.reply_to(message, f"{CE['🚀']} جاري ارسال {lines} سطر {CE['🚀']}")
    asyncio.create_task(send_tasteer_messages(user_id, target, lines, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['stop'])
async def stop(message):
    user_id = message.from_user.id
    if user_id in active_spams:
        active_spams[user_id]["stop"] = True
        try:
            await bot.send_sticker(message.chat.id, STICKERS["stop"])
        except:
            pass
        await bot.reply_to(message, f"{CE['🛑']} تم الايقاف {CE['🛑']}")
    else:
        await send_fancy_reply(message, f"{CE['⚠️']} لا توجد عملية {CE['⚠️']}", "warning")

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🔥 TNT SHADOW BOT شغال 🔥"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

async def main():
    print("🔥 TNT SHADOW BOT شغال 🔥")
    print(f"✅ التوكن: {BOT_TOKEN[:20]}...")
    print(f"✅ الأونر ID: {OWNER_ID}")
    print("✅ تم تفعيل الإيموجيات المميزة (tg-emoji)!")
    print("✅ تم تفعيل جميع الملصقات!")
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
