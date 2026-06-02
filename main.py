import asyncio
import re
import random
import os
import threading
import sqlite3
from datetime import datetime, timedelta
from telethon import TelegramClient
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask

# =============== TOKENS & IDs ===============
API_ID = 30874435
API_HASH = "cc3b98786456de26fe5e803910051cea"
BOT_TOKEN = "8811228549:AAGsFA1_LhxrGg0MBb1fdN47tBj9q2VjK4E"
OWNER_ID = 8619852744
OWNER_USERNAME = "@Dwojj"

# =============== إيموجيات تيليجرام الأصلية المميزة ===============
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
    '🎁': '<tg-emoji emoji-id="5976317950091598658">🎁</tg-emoji>',
    '⏰': '<tg-emoji emoji-id="5314299563761222650">⏰</tg-emoji>',
    '🛑': '<tg-emoji emoji-id="5888789252493283486">🛑</tg-emoji>',
    '📊': '<tg-emoji emoji-id="5935935761336505948">📊</tg-emoji>',
    '👤': '<tg-emoji emoji-id="5373020661574826232">👤</tg-emoji>',
    '⚙️': '<tg-emoji emoji-id="5857054220179480029">⚙️</tg-emoji>',
    '💰': '<tg-emoji emoji-id="6037182124916740433">💰</tg-emoji>',
    '✨': '<tg-emoji emoji-id="5254001839287859496">✨</tg-emoji>',
    '📱': '<tg-emoji emoji-id="5834628314731387616">📱</tg-emoji>',
    '💬': '<tg-emoji emoji-id="5314299563761222650">💬</tg-emoji>',
    '🔗': '<tg-emoji emoji-id="5967301267549068409">🔗</tg-emoji>',
    '📦': '<tg-emoji emoji-id="5881760620117760960">📦</tg-emoji>',
    '🛠️': '<tg-emoji emoji-id="5965466792527666087">🛠️</tg-emoji>',
    '📋': '<tg-emoji emoji-id="5803363345113290876">📋</tg-emoji>',
    '🏠': '<tg-emoji emoji-id="5881760620117760960">🏠</tg-emoji>',
}

def ce(text):
    if not text:
        return text
    for ch, replacement in CE.items():
        text = text.replace(ch, replacement)
    return text

def bq(text):
    return f"<blockquote>{ce(str(text))}</blockquote>"

# =============== قاعدة البيانات ===============
DB_PATH = "subscriptions.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (user_id TEXT PRIMARY KEY, expiry TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, first_name TEXT, username TEXT, join_date TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, first_name, username):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username, join_date) VALUES (?, ?, ?, ?)",
                  (str(user_id), first_name, username, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except:
        pass

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
        return False
    except:
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
    except:
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
    except:
        return "خطأ"

init_db()

# =============== الكيبوردات الرئيسية (زي الصورة) ===============
def get_main_keyboard():
    """الكيبورد اللي تحت - أزرار دائمة"""
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton(f"{CE['📦']} Commands {CE['📦']}"),
        KeyboardButton(f"{CE['🛠️']} Tools {CE['🛠️']}"),
        KeyboardButton(f"{CE['💰']} Pricing {CE['💰']}"),
        KeyboardButton(f"{CE['👤']} Profile {CE['👤']}"),
        KeyboardButton(f"{CE['💬']} Support {CE['💬']}")
    )
    return keyboard

def get_commands_keyboard():
    """كيبورد الأوامر"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(f"{CE['🔥']} تكليش {CE['🔥']}", callback_data="cmd_takleesh"),
        InlineKeyboardButton(f"{CE['⚙️']} تسطير {CE['⚙️']}", callback_data="cmd_tasteer"),
        InlineKeyboardButton(f"{CE['🔐']} تسجيل دخول {CE['🔐']}", callback_data="cmd_login"),
        InlineKeyboardButton(f"{CE['🛑']} إيقاف {CE['🛑']}", callback_data="cmd_stop"),
        InlineKeyboardButton(f"{CE['🎁']} اشتراك {CE['🎁']}", callback_data="cmd_subscribe"),
        InlineKeyboardButton(f"{CE['⏰']} متبقي {CE['⏰']}", callback_data="cmd_myplan"),
        InlineKeyboardButton(f"{CE['🏠']} الرئيسية {CE['🏠']}", callback_data="back_home")
    )
    return keyboard

def get_tools_keyboard():
    """كيبورد الأدوات"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(f"{CE['📱']} التحقق من رقم {CE['📱']}", callback_data="tool_check"),
        InlineKeyboardButton(f"{CE['🔗']} جلب معلومات {CE['🔗']}", callback_data="tool_info"),
        InlineKeyboardButton(f"{CE['🏠']} الرئيسية {CE['🏠']}", callback_data="back_home")
    )
    return keyboard

def get_pricing_keyboard():
    """كيبورد الأسعار"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(f"{CE['⭐']} ساعة - 15⭐", callback_data="sub_hour"),
        InlineKeyboardButton(f"{CE['💎']} يوم - 50💎", callback_data="sub_day"),
        InlineKeyboardButton(f"{CE['👑']} اسبوع - 150👑", callback_data="sub_week"),
        InlineKeyboardButton(f"{CE['🔥']} شهر - 250🔥", callback_data="sub_month"),
        InlineKeyboardButton(f"{CE['🏠']} الرئيسية {CE['🏠']}", callback_data="back_home")
    )
    return keyboard

def get_profile_keyboard():
    """كيبورد البروفايل"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(f"{CE['🎁']} تفعيل اشتراك {CE['🎁']}", callback_data="cmd_subscribe"),
        InlineKeyboardButton(f"{CE['🏠']} الرئيسية {CE['🏠']}", callback_data="back_home")
    )
    return keyboard

bot = AsyncTeleBot(BOT_TOKEN, parse_mode="HTML")

# =============== المتغيرات ===============
user_sessions = {}
active_spams = {}
user_steps = {}

# =============== دوال الهجوم ===============
VERBS_POWER = ["لحلكك", "اشيلك", "عبالك", "انيجمك", "مصمص"]
NOUNS_POWER = ["الهالبك", "بعيري", "تيزمك", "علصدرك", "قضيبي"]
INSULTS_POWER = ["يا ابن الكلب", "يا ابن الشرموطه", "يا ديوث", "يا خنيث"]
VERBS_EXTRA = ["كس امك", "كسمك", "انيك امك"]
SAUDI_STRONG = ["يابنالقحبه", "شرموطه", "خنيث"]
TASTEER_STRONG = ["كس امك", "كسمك", "انيك امك"]

def generate_takleesh():
    parts = [random.choice(VERBS_POWER), random.choice(NOUNS_POWER), random.choice(INSULTS_POWER), random.choice(VERBS_EXTRA)]
    return " ".join(parts)

def generate_tasteer():
    return random.choice([f"{random.choice(TASTEER_STRONG)} {random.choice(INSULTS_POWER)}", f"{random.choice(SAUDI_STRONG)} {random.choice(TASTEER_STRONG)}"])

# =============== دوال التليثون ===============
async def send_code_telethon(user_id, phone):
    try:
        client = TelegramClient(":memory:", 30874435, "cc3b98786456de26fe5e803910051cea")
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
    except Exception as e:
        return str(e)

def is_verified(user_id):
    return user_id in user_sessions and user_sessions[user_id].get("step") == "ready"

def get_client(user_id):
    return user_sessions.get(user_id, {}).get("client")

async def send_takleesh_messages(user_id, target, count, chat_id):
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, bq(f"{CE['❌']} اشتراك مطلوب: اشترك من زر الاشتراك {CE['❌']}"))
        return
    client = get_client(user_id)
    if not client:
        await bot.send_message(chat_id, bq(f"{CE['❌']} سجل دخول أولاً {CE['❌']}"))
        return
    for i in range(count):
        word = generate_takleesh()
        try:
            await client.send_message(target, word)
            await bot.send_message(chat_id, bq(f"{CE['✅']} [{i+1}/{count}] تم الارسال {CE['✅']}"))
        except Exception as e:
            await bot.send_message(chat_id, bq(f"{CE['❌']} فشل: {e} {CE['❌']}"))
            break
        await asyncio.sleep(3)
    await bot.send_message(chat_id, bq(f"{CE['✅']} اكتمل! {CE['✅']}"))

async def send_tasteer_messages(user_id, target, lines, chat_id):
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, bq(f"{CE['❌']} اشتراك مطلوب {CE['❌']}"))
        return
    client = get_client(user_id)
    if not client:
        await bot.send_message(chat_id, bq(f"{CE['❌']} سجل دخول أولاً {CE['❌']}"))
        return
    for i in range(lines):
        word = generate_tasteer()
        try:
            await client.send_message(target, word)
            await bot.send_message(chat_id, bq(f"{CE['✅']} [{i+1}/{lines}] تم الارسال {CE['✅']}"))
        except Exception as e:
            await bot.send_message(chat_id, bq(f"{CE['❌']} فشل: {e} {CE['❌']}"))
            break
        await asyncio.sleep(3)
    await bot.send_message(chat_id, bq(f"{CE['✅']} اكتمل! {CE['✅']}"))

# =============== أوامر البوت الرئيسية ===============
@bot.message_handler(commands=['start'])
async def start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    add_user(user_id, first_name, username)
    
    status = get_subscription_time(user_id)
    
    caption = f"""✨━━━━━━━━━━━━━━━━━━━━✨
{CE['🔥']} <b>TNT SHADOW BOT</b> {CE['🔥']}
✨━━━━━━━━━━━━━━━━━━━━✨

{CE['👤']} <b>Welcome {first_name}</b> {CE['👤']}
{CE['💎']} <b>Status</b> : {status}

✨━━━━━━━━━━━━━━━━━━━━✨
{CE['📦']} <b>Commands</b> {CE['📦']} | {CE['🛠️']} <b>Tools</b> {CE['🛠️']} | {CE['💰']} <b>Pricing</b> {CE['💰']}
✨━━━━━━━━━━━━━━━━━━━━✨

{CE['💬']} <b>Support</b> : {OWNER_USERNAME}

✨━━━━━━━━━━━━━━━━━━━━✨
{CE['⚙️']} <b>Click the buttons below</b> {CE['⚙️']}
"""
    
    await bot.send_message(message.chat.id, bq(caption), reply_markup=get_main_keyboard())

# =============== معالج الأزرار السفلية (Reply Keyboard) ===============
@bot.message_handler(func=lambda m: m.text and "Commands" in m.text)
async def commands_button(message):
    await bot.send_message(message.chat.id, bq(f"{CE['📦']} <b>Available Commands</b> {CE['📦']}"), reply_markup=get_commands_keyboard())

@bot.message_handler(func=lambda m: m.text and "Tools" in m.text)
async def tools_button(message):
    await bot.send_message(message.chat.id, bq(f"{CE['🛠️']} <b>Available Tools</b> {CE['🛠️']}"), reply_markup=get_tools_keyboard())

@bot.message_handler(func=lambda m: m.text and "Pricing" in m.text)
async def pricing_button(message):
    text = f"""💰━━━━━━━━━━━━━━━━━━━━💰
{CE['⭐']} <b>Subscription Plans</b> {CE['⭐']}
💰━━━━━━━━━━━━━━━━━━━━💰

{CE['⭐']} <b>1 Hour</b> → 15 Stars
{CE['💎']} <b>1 Day</b> → 50 Stars
{CE['👑']} <b>1 Week</b> → 150 Stars
{CE['🔥']} <b>1 Month</b> → 250 Stars

💰━━━━━━━━━━━━━━━━━━━━💰
{CE['💬']} <b>Contact</b> : {OWNER_USERNAME}
"""
    await bot.send_message(message.chat.id, bq(text), reply_markup=get_pricing_keyboard())

@bot.message_handler(func=lambda m: m.text and "Profile" in m.text)
async def profile_button(message):
    user_id = message.from_user.id
    status = get_subscription_time(user_id)
    text = f"""👤━━━━━━━━━━━━━━━━━━━━👤
{CE['👑']} <b>Your Profile</b> {CE['👑']}
👤━━━━━━━━━━━━━━━━━━━━👤

{CE['👤']} <b>ID</b> : <code>{user_id}</code>
{CE['💎']} <b>Status</b> : {status}

👤━━━━━━━━━━━━━━━━━━━━👤"""
    await bot.send_message(message.chat.id, bq(text), reply_markup=get_profile_keyboard())

@bot.message_handler(func=lambda m: m.text and "Support" in m.text)
async def support_button(message):
    text = f"""💬━━━━━━━━━━━━━━━━━━━━💬
{CE['👑']} <b>Support Center</b> {CE['👑']}
💬━━━━━━━━━━━━━━━━━━━━💬

{CE['🔗']} <b>Developer</b> : {OWNER_USERNAME}
{CE['💬']} <b>Channel</b> : @TNT_SHADOW

💬━━━━━━━━━━━━━━━━━━━━💬"""
    await bot.send_message(message.chat.id, bq(text), reply_markup=get_main_keyboard())

# =============== معالج الأزرار الإنلاين (Inline Keyboard) ===============
@bot.callback_query_handler(func=lambda call: True)
async def callback_handler(call):
    user_id = call.from_user.id
    
    if call.data == "back_home":
        await bot.edit_message_text(
            bq(f"{CE['🏠']} <b>Back to Home</b> {CE['🏠']}"),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_keyboard()
        )
        return
    
    elif call.data == "cmd_takleesh":
        if not is_subscribed(user_id):
            await bot.answer_callback_query(call.id, "اشتراك مطلوب!", show_alert=True)
            return
        if not is_verified(user_id):
            await bot.answer_callback_query(call.id, "سجل دخول أولاً!", show_alert=True)
            return
        user_steps[user_id] = {"step": "takleesh_target"}
        await bot.send_message(call.message.chat.id, bq(f"{CE['🎯']} ارسل معرف المستهدف (@username):"))
    
    elif call.data == "cmd_tasteer":
        if not is_subscribed(user_id):
            await bot.answer_callback_query(call.id, "اشتراك مطلوب!", show_alert=True)
            return
        if not is_verified(user_id):
            await bot.answer_callback_query(call.id, "سجل دخول أولاً!", show_alert=True)
            return
        user_steps[user_id] = {"step": "tasteer_target"}
        await bot.send_message(call.message.chat.id, bq(f"{CE['🎯']} ارسل معرف المستهدف (@username):"))
    
    elif call.data == "cmd_login":
        if not is_subscribed(user_id):
            await bot.answer_callback_query(call.id, "اشتراك مطلوب!", show_alert=True)
            return
        if is_verified(user_id):
            await bot.answer_callback_query(call.id, "مسجل بالفعل!", show_alert=True)
            return
        user_steps[user_id] = {"step": "waiting_phone"}
        await bot.send_message(call.message.chat.id, bq(f"{CE['🔐']} ارسل رقمك مع +\nمثال: +966512345678"))
    
    elif call.data == "cmd_stop":
        if user_id in active_spams:
            active_spams[user_id]["stop"] = True
            await bot.answer_callback_query(call.id, "تم الإيقاف!")
        else:
            await bot.answer_callback_query(call.id, "لا توجد عملية!")
    
    elif call.data == "cmd_subscribe":
        await bot.send_message(call.message.chat.id, bq(f"{CE['🎁']} اختر الباقة:"), reply_markup=get_pricing_keyboard())
    
    elif call.data == "cmd_myplan":
        status = get_subscription_time(user_id)
        await bot.answer_callback_query(call.id, f"حالتك: {status}", show_alert=True)
    
    elif call.data.startswith("sub_"):
        plans = {
            "sub_hour": {"hours": 1, "name": "ساعة", "price": 15},
            "sub_day": {"hours": 24, "name": "يوم", "price": 50},
            "sub_week": {"hours": 168, "name": "اسبوع", "price": 150},
            "sub_month": {"hours": 720, "name": "شهر", "price": 250}
        }
        plan = plans.get(call.data)
        if plan:
            add_subscription(user_id, plan["hours"])
            await bot.answer_callback_query(call.id, f"تم تفعيل اشتراك {plan['name']}!")
            await bot.send_message(call.message.chat.id, bq(f"{CE['✅']} تم تفعيل اشتراك {plan['name']} {CE['✅']}"))
    
    elif call.data == "tool_check":
        await bot.answer_callback_query(call.id, "🚧 قريباً")
    
    elif call.data == "tool_info":
        await bot.answer_callback_query(call.id, "🚧 قريباً")

# =============== معالج الخطوات ===============
@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_phone")
async def handle_phone(message):
    user_id = message.from_user.id
    phone = message.text.strip()
    if not phone.startswith('+'):
        await bot.reply_to(message, bq(f"{CE['❌']} الرقم يبدأ بـ +"))
        return
    await bot.reply_to(message, bq(f"{CE['⏰']} جاري ارسال الكود..."))
    result = await send_code_telethon(user_id, phone)
    if result is True:
        user_steps[user_id] = {"step": "waiting_code"}
        await bot.send_message(message.chat.id, bq(f"{CE['✅']} تم ارسال الكود\nادخل الكود:"))
    else:
        await bot.reply_to(message, bq(f"{CE['❌']} فشل: {result}"))
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_code")
async def handle_code(message):
    user_id = message.from_user.id
    code = message.text.strip()
    result = await verify_code_telethon(user_id, code)
    if result is True:
        del user_steps[user_id]
        await bot.reply_to(message, bq(f"{CE['✅']} تم الدخول بنجاح!"))
    else:
        await bot.reply_to(message, bq(f"{CE['❌']} كود خطأ"))
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_target")
async def handle_takleesh_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "takleesh_count", "target": target}
    await bot.reply_to(message, bq(f"{CE['📊']} عدد الرسائل:"))

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_count")
async def handle_takleesh_count(message):
    user_id = message.from_user.id
    try:
        count = int(message.text.strip())
        target = user_steps[user_id]["target"]
        await bot.reply_to(message, bq(f"{CE['🚀']} جاري ارسال {count} رسالة..."))
        asyncio.create_task(send_takleesh_messages(user_id, target, count, message.chat.id))
        del user_steps[user_id]
    except:
        await bot.reply_to(message, bq(f"{CE['❌']} عدد غير صالح"))
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_target")
async def handle_tasteer_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "tasteer_lines", "target": target}
    await bot.reply_to(message, bq(f"{CE['📊']} عدد الاسطر:"))

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_lines")
async def handle_tasteer_lines(message):
    user_id = message.from_user.id
    try:
        lines = int(message.text.strip())
        target = user_steps[user_id]["target"]
        await bot.reply_to(message, bq(f"{CE['🚀']} جاري ارسال {lines} سطر..."))
        asyncio.create_task(send_tasteer_messages(user_id, target, lines, message.chat.id))
        del user_steps[user_id]
    except:
        await bot.reply_to(message, bq(f"{CE['❌']} عدد غير صالح"))
        del user_steps[user_id]

# =============== فلاسك ===============
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "TNT SHADOW BOT Running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

async def main():
    print("🔥 TNT SHADOW BOT شغال 🔥")
    print("✅ بوت زي الصورة بالضبط!")
    print("✅ أزرار تحت وفوق!")
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
