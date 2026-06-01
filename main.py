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

API_ID = 30874435
API_HASH = "cc3b98786456de26fe5e803910051cea"
BOT_TOKEN = "8817608659:AAF8O-I58x-khZLq4AzY-OWTyfgPIcNEo1M"
OWNER_ID = 8603631953

user_sessions = {}
active_spams = {}
user_steps = {}

DB_PATH = "subscriptions.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (user_id TEXT PRIMARY KEY, expiry TEXT)''')
    conn.commit()
    conn.close()

def is_subscribed(user_id):
    user_id = str(user_id)
    if user_id == str(OWNER_ID):
        return True
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT expiry FROM subscriptions WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        expiry = datetime.fromisoformat(row[0])
        if datetime.now() < expiry:
            return True
        else:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
    return False

def add_subscription(user_id, duration_hours):
    user_id = str(user_id)
    expiry = datetime.now() + timedelta(hours=duration_hours)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)", (user_id, expiry.isoformat()))
    conn.commit()
    conn.close()

def get_subscription_time(user_id):
    user_id = str(user_id)
    if user_id == str(OWNER_ID):
        return "دائم (الأونر)"
    conn = sqlite3.connect(DB_PATH)
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
            return f"{hours} ساعة و {minutes} دقيقة متبقية"
        elif minutes > 0:
            return f"{minutes} دقيقة متبقية"
    return "غير مشترك"

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
add_subscription(OWNER_ID, 87600)

# =============== أجزاء الكليشات (توليد ملايين الكليشات) ===============
PREFIXES1 = [
    "لحلكك", "اشيلك", "عبالك", "انيجمك", "مصمص", "اهف", "اربطك", "اطحن", "اكهرب", "احط",
    "اقتحم", "اخدر", "انيج", "ربك", "اعبد", "ادحس", "افلش", "اذب", "اكعد", "ازورك", "اصعق",
    "اطشر", "اعجن", "اشكه", "اشنقك", "ابعبص", "اتفل", "اتسودن", "اتنايج", "اخرمش", "انكز",
    "اصمل", "اضرب", "اخلي", "ارمي", "احبس", "اذبح", "احرق", "اخرب", "ادمر"
]

PREFIXES2 = [
    "الهالبك", "بعيري", "تيزمك", "علصدرك", "عيورتي", "بقياطين", "ضلوعك", "قضيبي", "نسلك",
    "زبي", "صريمك", "كسمك", "بكسختك", "براسك", "لكسمك", "بطيزك", "بكس امك", "بكسم اختك",
    "بطيز اختك", "بكسم خويك", "بكس خواتك", "ديوسك", "نهود امك", "صرمك", "مخك", "طيزك",
    "كس اختك", "كس امك", "عيري", "جبتي", "ربعك", "خواتك", "عيالك", "نياكة", "ديوس اختك"
]

PREFIXES3 = [
    "يا ابن الكلب", "يا ابن الشرموطه", "يا ابن القحبه", "يا ديوث", "يا خنيث", "يا ابن المتناكه",
    "يا ابن العاهره", "يا ابن الدعاره", "يا ابن الزانيه", "يا ابن الكحبه", "يا ابن العرص",
    "يا خول", "يا جرار", "يا منيوك", "يا فحل اختك", "يا فحل امك", "يا ابن الحمار", "يا ابن البقره",
    "يا ابن الخنزير", "يا كلب", "يا حمار", "يا تيس", "يا قرد", "يا خنزير", "يا نجس", "يا رجس",
    "يا وسخ", "يا جربان", "يا معفن", "يا خبيث", "يا رذيل", "يا حقير", "يا دنيء", "يا فاسق"
]

PREFIXES4 = [
    "كس امك", "كسمك", "كس اختك", "كسم امك", "كس عرضك", "كسم عرضك", "انيك امك", "انيك اختك",
    "انيك كس امك", "انيك كس اختك", "اطحن مخك", "افطر كبدك", "اشرب دمك", "اكل لحمك", "احرق بيتكم",
    "اخرب عليك", "افضحك", "احرجك", "فضحتنا", "اخليك تندم", "اخليك تبكي", "اخليك تصيح",
    "اخلي عيالك يبكون", "اخلي زوجتك تطلقك", "اخلي اهلك يتبرون منك", "ادمر حياتك", "اخليك فاشل"
]

# توليد كليشة عشوائية (ملايين الاحتمالات)
def generate_millions_takleesh():
    # تجميع أجزاء عشوائية
    parts = []
    parts.append(random.choice(PREFIXES1))
    parts.append(random.choice(PREFIXES2))
    parts.append(random.choice(PREFIXES3))
    
    # إضافة كلمات قوية (70% فرصة)
    if random.random() > 0.3:
        parts.append(random.choice(PREFIXES4))
        parts.append(random.choice(PREFIXES3))
    
    # إضافة كلمات إضافية (50% فرصة)
    if random.random() > 0.5:
        parts.append("و")
        parts.append(random.choice(PREFIXES4))
    
    return " ".join(parts)

# توليد كلمة تسطير عشوائية (ملايين الاحتمالات)
def generate_millions_tasteer():
    patterns = [
        f"{random.choice(PREFIXES4)} {random.choice(PREFIXES3)}",
        f"{random.choice(PREFIXES3)} {random.choice(PREFIXES4)}",
        f"يا {random.choice(PREFIXES3)} يا {random.choice(PREFIXES3)}",
        f"{random.choice(PREFIXES4)} يا {random.choice(PREFIXES3)}",
        f"{random.choice(PREFIXES3)} {random.choice(PREFIXES4)} يا خنيث",
        f"{random.choice(PREFIXES4)} {random.choice(PREFIXES4)}",
        f"انيك {random.choice(PREFIXES3)} و{random.choice(PREFIXES4)}",
        f"{random.choice(PREFIXES3)} انت واهلك كلهم {random.choice(PREFIXES4)}"
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
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe")
        return
    if user_id in active_spams:
        active_spams[user_id]["stop"] = False
    else:
        active_spams[user_id] = {"stop": False}
    client = get_client(user_id)
    if not client:
        await bot.send_message(chat_id, "❌ خطأ في الجلسة")
        return
    for i in range(count):
        if active_spams[user_id]["stop"]:
            await bot.send_message(chat_id, "🛑 تم الإيقاف")
            break
        word = generate_millions_takleesh()
        try:
            await client.send_message(target, word)
        except Exception as e:
            await bot.send_message(chat_id, f"❌ فشل: {str(e)}")
            break
        await asyncio.sleep(1)
    await bot.send_message(chat_id, f"✅ تم إرسال {count} كليشة")
    if user_id in active_spams:
        del active_spams[user_id]

async def send_tasteer_messages(user_id, target, lines, delay, chat_id):
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe")
        return
    if user_id in active_spams:
        active_spams[user_id]["stop"] = False
    else:
        active_spams[user_id] = {"stop": False}
    client = get_client(user_id)
    if not client:
        await bot.send_message(chat_id, "❌ خطأ في الجلسة")
        return
    for i in range(lines):
        if active_spams[user_id]["stop"]:
            await bot.send_message(chat_id, "🛑 تم الإيقاف")
            break
        word = generate_millions_tasteer()
        try:
            await client.send_message(target, word)
        except Exception as e:
            await bot.send_message(chat_id, f"❌ فشل: {str(e)}")
            break
        await asyncio.sleep(delay)
    await bot.send_message(chat_id, f"✅ تم إرسال {lines} سطر تسطير")
    if user_id in active_spams:
        del active_spams[user_id]

@bot.message_handler(commands=['start'])
async def start(message):
    status = get_subscription_time(message.from_user.id)
    await bot.reply_to(message, f"""
🔥 فشار بوت الاحترافي 🔥

━━━━━━━━━━━━━━━━━━━━
🤖 المبرمج: الداهية ايليا الملائكة
👑 الاونر: @Dwojj
━━━━━━━━━━━━━━━━━━━━

📊 حالتك: {status}

⚡ الأوامر:
/login - تسجيل دخول
/takleesh - تكليش (ملايين الكليشات)
/tasteer - تسطير (ملايين الكلمات)
/stop - إيقاف
/subscribe - اشتراك
/myplan - باقي الاشتراك
/gift - للأونر فقط

💪 ملايين الكليشات المختلفة
💪 ملايين كلمات التسطير
""")

@bot.message_handler(commands=['subscribe'])
async def subscribe(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⭐ ساعة - 15 نجمة", callback_data="sub_hour"),
        InlineKeyboardButton("⭐ يوم - 50 نجمة", callback_data="sub_day"),
        InlineKeyboardButton("⭐ اسبوع - 150 نجمة", callback_data="sub_week"),
        InlineKeyboardButton("⭐ شهر - 250 نجمة", callback_data="sub_month")
    )
    await bot.reply_to(message, "⭐ اختر مدة الاشتراك:", reply_markup=markup)

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
            description=f"⭐ {plan['stars']} نجمة - {plan['name']}",
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
    if "ساعة" in payload:
        add_subscription(user_id, 1)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة ساعة")
    elif "يوم" in payload:
        add_subscription(user_id, 24)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة يوم")
    elif "اسبوع" in payload:
        add_subscription(user_id, 168)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة اسبوع")
    elif "شهر" in payload:
        add_subscription(user_id, 720)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة شهر")

@bot.message_handler(commands=['myplan'])
async def myplan(message):
    await bot.reply_to(message, f"📊 حالتك: {get_subscription_time(message.from_user.id)}")

@bot.message_handler(commands=['gift'])
async def gift_subscription(message):
    if message.from_user.id != OWNER_ID:
        await bot.reply_to(message, "❌ للأونر فقط @Dwojj")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await bot.reply_to(message, "/gift [ايدي] [مدة]\nمثال: /gift 8619852744 5 دقائق")
        return
    try:
        target_id = int(args[1])
        hours = parse_duration(args[2])
        if hours:
            add_subscription(target_id, hours)
            await bot.reply_to(message, f"✅ تم تفعيل اشتراك {target_id} لمدة {args[2]}")
            try:
                await bot.send_message(target_id, f"🎁 تم تفعيل اشتراك لك لمدة {args[2]} بواسطة الأونر @Dwojj")
            except:
                pass
    except:
        await bot.reply_to(message, "❌ خطأ")

@bot.message_handler(commands=['login'])
async def login(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ اشتراك مطلوب: /subscribe")
        return
    if is_verified(user_id):
        await bot.reply_to(message, "✅ مسجل بالفعل")
        return
    user_steps[user_id] = {"step": "waiting_phone"}
    await bot.reply_to(message, "📱 أرسل رقمك مع +\nمثال: +966512345678")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_phone")
async def handle_phone(message):
    user_id = message.from_user.id
    phone = message.text.strip()
    if not phone.startswith('+'):
        await bot.reply_to(message, "❌ الرقم يبدأ بـ +")
        return
    await bot.reply_to(message, "⏳ جاري إرسال الكود...")
    result = await send_code_telethon(user_id, phone)
    if result is True:
        user_steps[user_id] = {"step": "waiting_code"}
        await bot.reply_to(message, "✅ تم إرسال الكود\nأدخل الكود بمسافات:\nمثال: 1 2 3 4 5")
    else:
        await bot.reply_to(message, f"❌ فشل: {result}")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_code")
async def handle_code(message):
    user_id = message.from_user.id
    code = message.text.strip().replace(" ", "")
    if not code.isdigit():
        await bot.reply_to(message, "❌ الكود أرقام فقط")
        return
    result = await verify_code_telethon(user_id, code)
    if result is True:
        del user_steps[user_id]
        await bot.reply_to(message, "✅ تم الدخول\n/takleesh\n/tasteer")
    elif result == "password_needed":
        user_steps[user_id] = {"step": "waiting_password"}
        await bot.reply_to(message, "🔐 أرسل كلمة المرور:")
    else:
        await bot.reply_to(message, "❌ كود خطأ")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_password")
async def handle_password(message):
    user_id = message.from_user.id
    password = message.text.strip()
    result = await verify_password_telethon(user_id, password)
    if result is True:
        del user_steps[user_id]
        await bot.reply_to(message, "✅ تم الدخول")
    else:
        await bot.reply_to(message, "❌ كلمة مرور خطأ")
        del user_steps[user_id]

@bot.message_handler(commands=['takleesh'])
async def takleesh(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ اشتراك مطلوب: /subscribe")
        return
    if not is_verified(user_id):
        await bot.reply_to(message, "❌ سجل دخول: /login")
        return
    if user_id in active_spams:
        await bot.reply_to(message, "⚠️ عملية شغالة: /stop")
        return
    user_steps[user_id] = {"step": "takleesh_target"}
    await bot.reply_to(message, "🎯 أرسل معرف المستهدف (@username أو ID):")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_target")
async def takleesh_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "takleesh_count", "target": target}
    await bot.reply_to(message, "🔢 كم رسالة؟")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_count")
async def takleesh_count(message):
    user_id = message.from_user.id
    try:
        count = int(message.text.strip())
        if count < 1:
            raise ValueError
    except:
        await bot.reply_to(message, "❌ عدد غير صالح")
        del user_steps[user_id]
        return
    target = user_steps[user_id]["target"]
    await bot.reply_to(message, f"⚡ بدء إرسال {count} كليشة")
    asyncio.create_task(send_takleesh_messages(user_id, target, count, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['tasteer'])
async def tasteer(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ اشتراك مطلوب: /subscribe")
        return
    if not is_verified(user_id):
        await bot.reply_to(message, "❌ سجل دخول: /login")
        return
    if user_id in active_spams:
        await bot.reply_to(message, "⚠️ عملية شغالة: /stop")
        return
    user_steps[user_id] = {"step": "tasteer_target"}
    await bot.reply_to(message, "🎯 أرسل معرف المستهدف (@username أو ID):")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_target")
async def tasteer_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "tasteer_lines", "target": target}
    await bot.reply_to(message, "🔢 كم سطر تريد إرسالها؟")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_lines")
async def tasteer_lines(message):
    user_id = message.from_user.id
    try:
        lines = int(message.text.strip())
        if lines < 1:
            raise ValueError
    except:
        await bot.reply_to(message, "❌ عدد غير صالح")
        del user_steps[user_id]
        return
    user_steps[user_id] = {"step": "tasteer_delay", "target": user_steps[user_id]["target"], "lines": lines}
    await bot.reply_to(message, "⏱️ السرعة (ثانية):")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_delay")
async def tasteer_delay(message):
    user_id = message.from_user.id
    try:
        delay = float(message.text.strip())
        if delay < 0.5:
            raise ValueError
    except:
        await bot.reply_to(message, "❌ سرعة غير صالحة")
        del user_steps[user_id]
        return
    target = user_steps[user_id]["target"]
    lines = user_steps[user_id]["lines"]
    await bot.reply_to(message, f"🚀 بدء إرسال {lines} سطر")
    asyncio.create_task(send_tasteer_messages(user_id, target, lines, delay, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['stop'])
async def stop(message):
    user_id = message.from_user.id
    if user_id in active_spams:
        active_spams[user_id]["stop"] = True
        await bot.reply_to(message, "🛑 جاري الإيقاف")
    else:
        await bot.reply_to(message, "⚠️ ما فيه عملية")

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Shadow Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

async def main():
    print("SHADOW BOT is running...")
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())    c = conn.cursor()
    c.execute("SELECT expiry FROM subscriptions WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        expiry = datetime.fromisoformat(row[0])
        if datetime.now() < expiry:
            return True
        else:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
    return False

def add_subscription(user_id, duration_hours):
    user_id = str(user_id)
    expiry = datetime.now() + timedelta(hours=duration_hours)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)", (user_id, expiry.isoformat()))
    conn.commit()
    conn.close()

def get_subscription_time(user_id):
    user_id = str(user_id)
    if user_id == str(OWNER_ID):
        return "دائم (الأونر)"
    conn = sqlite3.connect(DB_PATH)
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
            return f"{hours} ساعة و {minutes} دقيقة متبقية"
        elif minutes > 0:
            return f"{minutes} دقيقة متبقية"
    return "غير مشترك"

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
add_subscription(OWNER_ID, 87600)

# =============== كلمات طويلة جداً للتكليش ===============
ULTRA_LONG_TAKLEESH = [
    """ياخي يا ابن الكلب يا ابن الشرموطه يا ابن القحبه يا ابن العاهره يا ابن الدعاره يا ابن المتناكه يا ابن الزانيه يا ابن الكحبه يا ابن العرص يا ابن الخنزير يا ابن الحمار يا ابن البقره يا ابن الكس، والله اني راح انيك كس امك قدام اخواتك واهلك كلهم، واخليك تندم انك انولدت يا ديوث يا خنيث يا جرار يا منيوك يا فحل اختك يا فحل امك، راح اخلي عيالك يتسولون في الشوارع وراح اخلي زوجتك تطلق منك وراح اخلي بيتك يخرب عليك، كس اختك كسمك كس عرضك كسم عرضك انيك امك 100 مرة قدام الجيران، اطلق عليك طلقة وحدة تخليك تنام في المستشفى 6 شهور، راح اشيلك بعيري يا ابن الزنا وارميك في الزباله مثل الكلب اللي انتا""",

    """لحلكك الهالبك طيزمك يا ابن الكلب، والله العظيم العلي القدير اني راح انيك كس امك واخليها تصيح وتبكي قدام الملأ، راح اربطك بقياطين قندرتي واسحبك في الشارع مثل الكلب اليايع، راح اكسخك كسخه تخلي عيالك يتمنون موتك، راح اشيل ربك واركعه بلكاع يا خنيث يا ابن الديوث، انت وكل خواتك كحبات وانت ديوث كبير يا ابن الشرموطه، والله اني راح افتح كس امك على قده واخليها تتذكر ايام الشباب، كس اختك كس خواتك كس زوجتك كس بنتك، انيككم جميعاً واحد واحد، راح اخلليك تاكل تراب وتركض ورا عيري يا جبان يا تيس يا حمار يا كلب""",

    """عبالك اني اعوفك؟ يا ابن القحبه يا ابن العاهره، والله اني راح انيك كس اختك وتصير حامل مني وتجيب عيال زيك كلاب شوارع، راح اطحن ضلوعك واخلطها بالاسمنت وابني فيها حمام، راح اكهرب طيزك واخليك تقفز زي القرد في السيرك، راح احط قضيبي بكس امك قدام الحلال والحرام واخلي الكل يشوف، راح اقتحم بيتكم واخلي عيالك عبيد عندي يا ابن الزنا، انت ما تسوى حتى ريحة عيري يا ديوث يا خنيث يا جرار، والله اني راح اخليك تاكل خرا وتشرب بول يا ابن الكلب، كس امك كس اختك كس خواتك كس اهلك كلهم، انيك الجميع""",

    """اشيلك بعيري يا ابن الشرموطه يا ابن المتناكه، والله العظيم راح اخليك نادم على اليوم اللي جيت فيه، راح اربطك وارميك في البحر تاكل سمك، راح اخرمش طيزك واخليها تقرحات، راح افلشك تفليش واخليك تشحت عند اخواتك، راح اذوب تيزاب في كسمك واخليك تموت من العذاب، راح انيك امك واختك وزوجتك وبناتك كلهم في ليلة وحدة، راح اصعق صريمك واخليك تتخيل نياكتي طول عمرك، يا ديوث يا خنيث يا ابن الديوث يا فحل اختك، والله اني راح اخليك تتمنى الموت مليون مرة، كسمك كس عرضك كس امك كس اختك كس خواتك""",

    """انيجمك علصدرك يا ابن الزانيه يا ابن الكلب، والله اني راح احط عيري بفمك وتلحسه مثل المصاصه، راح اخليك ترقص عريان في الشارع والناس تتصور معك، راح افتضحك بين اهلك واصحابك واخلي الكل يعرف انك ديوث، راح اخللي مراتك ترميك وتهرب مع عشيقها، راح ابيع بيتك واخذ فلوسه، راح ادمر مستقبل عيالك واخلص عليهم، انت ولا شي يا جبان يا خول يا منيوك، والله اني راح انيك كس امك قدام الجامع عشان الكل يشوف، كسمك كس عرضك انيك 1000 مرة""",

    """مصمص عيورتي يا ابن العاهره يا ابن القحبه، والله اني راح اطعمك لحمة كلبي وتاكلها وانت تبكي، راح اخليك تحسد الفيران الي يعيشون في الزباله، راح احط راسك في المرحاض واخليك تغسل اسنانك بخراي، راح اخليك تنام في الشارع مثل المشردين، راح ادمر صحتك النفسية والجسدية واخلص عليك، يا ديوث يا خنيث يا ابن الديوث يا فحل اختك، والله اني راح انيك كس خواتك قدام عيالك واخليهم يشوفون ويزعلون، كسمك كس عرضك كس امك كس اختك""",

    """اهف اختك بطرف عيري يا ديوث يا ابن الشرموطه، والله اني راح اخليها تصير اشهر شرموطه في الحاره، راح اخلليها تنام مع الكلاب وتدفع فلوس عشان تنام معهم، راح احملها وتجيب عيال كلاب زيك، راح افتضحها في التيك توك واليوتيوب واخلي الكل يشوف، راح ادمر سمعتها واخليها تنتحر من العار، انت ديوث كبير يا ابن الديوث، والله اني راح انيك كس امك قدام الكعبة واخلي الحجاج يستغفرون، كسمك كس اختك كس خواتك كس اهلك""",

    """اربطك بقياطين قندرتي يا ابن الكحبه يا ابن المتناكه، والله اني راح اسحبك من طيزك في الشارع والناس تتصور معك، راح اخليك تلعب في الزباله وتاكل خراي الكلاب، راح اخليك تشرب من المرحاض وتفرح، راح ادمر حياتك وشكلك وسمعتك واخليك نادم، يا خنيث يا جرار يا فحل اختك يا فحل امك، والله اني راح انيك كس امك مليون مرة واخليها تصير معاقه جنسياً، كسمك كس عرضك انيكك يومياً""",

    """اطحن ضلوعك يا ابن القحبه يا ابن العاهره، والله اني راح اخلطها مع الخراسان وابني فيها سجن لك، راح اخليك تعيش طول عمرك في السجن وانت تبكي، راح ادمر احلامك وطموحاتك واخليك فاشل، راح اسبب لك امراض نفسية وجسدية وتصير مجنون، يا ديوث يا خنيث يا ابن الديوث، والله اني راح انيك كس اختك قدام زوجها واخليه يطلقها، كس امك كس اختك كس خواتك""",

    """اكهرب طيزك يا ابن الشرموطه يا ابن الدعاره، والله اني راح اخليك تقفز وتطير من الكهرب، راح اخليك تصيح وتصرخ والناس تسمع، راح اخليك تركض ورا عيري وانت تبكي، راح ادمر صحتك وتصير معاق كهربائياً، يا جبان يا خول يا منيوك، والله اني راح انيك كس امك قدام الملأ واخلي الكل يشوف، كسمك كس عرضك انيكك كل يوم""",
]

# =============== كلمات التسطير (آلاف الكلمات السعودية) ===============
SAUDI_TWORDS = [
    "كس امك", "كسمك", "كس اختك", "كسم امك", "كس عرضك", "كسم عرضك", "انيك امك", "انيك اختك",
    "انيك كس امك", "انيك كس اختك", "اطحن مخك", "افطر كبدك", "اشرب دمك", "اكل لحمك", "احرق بيتكم",
    "اخرب عليك", "افضحك", "احرجك", "فضحتنا", "يا ديوث", "يا خنيث", "يا ابن الكلب", "يا ابن الشرموطه",
    "يا ابن القحبه", "يا ابن العاهره", "يا ابن الدعاره", "يا ابن المتناكه", "يا ابن الزانيه", "يا ابن الكحبه",
    "يا ابن العرص", "يا ابن الخنزير", "يا ابن الحمار", "يا ابن البقره", "يا ابن الكس", "يا جرار", "يا منيوك",
    "يا خول", "يا قواد", "يا تيس", "يا حمار", "يا كلب", "يا خنزير", "يا قرد", "يا نجس", "يا رجس", "يا وسخ",
    "يا جربان", "يا معفن", "يا خبيث", "يا رذيل", "يا حقير", "يا دنيء", "يا فاسق", "يا فاجر", "يا ملوث",
    "كس اختك يا ديوث", "كسمك يا شرموطه", "كسم امك يا ابن العاهره", "ديوث يا ابن الديوث", "خنيث يا ابن الخنيث",
    "شرموطه يا ابن الشرموطه", "قحبه يا ابن القحبه", "قواد يا ابن القواد", "منيوك يا ابن المنيوك",
    "يا فحل اختك", "يا فحل امك", "يا ابن الساقطه", "يا فحل خواتك", "شو بك كس امك", "مسوي تسوي غبي صح",
    "يا ديوث يا جرار", "يا ابن الزقتين", "يا ابن الحزانه", "عار امك", "يا مخنث", "يا ابن الكس",
    "يا ابن الهايته", "ياخي انتهى", "اقعد مكانك", "لا تتحرك", "اسكت", "خر", "طلع برا", "اقفل فمك",
    "لا تنبح", "انت ولا شي", "انت تافه", "انت حقير", "انت فاشل", "انت جبان", "انت خول", "انت ديوث",
    "انت خنيث", "انت حمار", "انت كلب", "انت خنزير", "انت قرد", "انت تيس", "يا كس ام اهلك",
    "يا كس اخت اهلك", "يا كس خواتك", "انيك عيلتك كلها", "انيك اهلك كلهم", "اطلع برا حياتي",
    "لا تشوف وجهي", "اكرهك", "مقتك", "الله لا يوفقك", "الله يخزيك", "الله يذلك", "الله يفضحك",
    "اللعنة عليك", "عليك العار", "عليك الذل", "عليك الفضايح", "كل يوم وانت مصيبه", "ربك ياخذك",
    "الموت لك", "المرض لك", "الخراب لك", "التشريد لك", "لعنك الله", "طردك الله", "ابعد عن وجهي"
]

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

def generate_ultra_long_takleesh():
    return random.choice(ULTRA_LONG_TAKLEESH)

def generate_saudi_tasteer():
    return random.choice(SAUDI_TWORDS)

async def send_takleesh_messages(user_id, target, count, chat_id):
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe")
        return
    if user_id in active_spams:
        active_spams[user_id]["stop"] = False
    else:
        active_spams[user_id] = {"stop": False}
    client = get_client(user_id)
    if not client:
        await bot.send_message(chat_id, "❌ خطأ في الجلسة")
        return
    for i in range(count):
        if active_spams[user_id]["stop"]:
            await bot.send_message(chat_id, "🛑 تم الإيقاف")
            break
        word = generate_ultra_long_takleesh()
        try:
            await client.send_message(target, word)
        except Exception as e:
            await bot.send_message(chat_id, f"❌ فشل: {str(e)}")
            break
        await asyncio.sleep(1)
    await bot.send_message(chat_id, f"✅ تم إرسال {count} كليشة طويلة")
    if user_id in active_spams:
        del active_spams[user_id]

async def send_tasteer_messages(user_id, target, lines, delay, chat_id):
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe")
        return
    if user_id in active_spams:
        active_spams[user_id]["stop"] = False
    else:
        active_spams[user_id] = {"stop": False}
    client = get_client(user_id)
    if not client:
        await bot.send_message(chat_id, "❌ خطأ في الجلسة")
        return
    for i in range(lines):
        if active_spams[user_id]["stop"]:
            await bot.send_message(chat_id, "🛑 تم الإيقاف")
            break
        word = generate_saudi_tasteer()
        try:
            await client.send_message(target, word)
        except Exception as e:
            await bot.send_message(chat_id, f"❌ فشل: {str(e)}")
            break
        await asyncio.sleep(delay)
    await bot.send_message(chat_id, f"✅ تم إرسال {lines} سطر تسطير")
    if user_id in active_spams:
        del active_spams[user_id]

@bot.message_handler(commands=['start'])
async def start(message):
    status = get_subscription_time(message.from_user.id)
    await bot.reply_to(message, f"""
🔥 بوت فشار الاحترافي 🔥

━━━━━━━━━━━━━━━━━━━━
🤖 المبرمج: الداهية ايليا الملائكة
👑 الاونر: @Dwojj
━━━━━━━━━━━━━━━━━━━━

📊 حالة الاشتراك: {status}

⚡ الأوامر المتاحة:
/login - تسجيل الدخول
/takleesh - تكليش طويل جداً
/tasteer - تسطير قوي
/stop - إيقاف العملية
/subscribe - اشتراك بالنجوم
/myplan - معرفة باقي الاشتراك
/gift - للأونر فقط

💪 فيه كليشات طويلة جداً (اكثر من 50 كلمة)
💪 فيه آلاف الكلمات السعودية القوية
""")

@bot.message_handler(commands=['subscribe'])
async def subscribe(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⭐ ساعة - 15 نجمة", callback_data="sub_hour"),
        InlineKeyboardButton("⭐ يوم - 50 نجمة", callback_data="sub_day"),
        InlineKeyboardButton("⭐ اسبوع - 150 نجمة", callback_data="sub_week"),
        InlineKeyboardButton("⭐ شهر - 250 نجمة", callback_data="sub_month")
    )
    await bot.reply_to(message, "⭐ اختر مدة الاشتراك:", reply_markup=markup)

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
            title=f"اشتراك {plan['name']} - فشار بوت",
            description=f"تفعيل اشتراك {plan['name']}\n⭐ {plan['stars']} نجمة\n⏰ {plan['name']}",
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
    if "ساعة" in payload:
        add_subscription(user_id, 1)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة ساعة")
    elif "يوم" in payload:
        add_subscription(user_id, 24)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة يوم")
    elif "اسبوع" in payload:
        add_subscription(user_id, 168)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة اسبوع")
    elif "شهر" in payload:
        add_subscription(user_id, 720)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة شهر")

@bot.message_handler(commands=['myplan'])
async def myplan(message):
    await bot.reply_to(message, f"📊 حالتك: {get_subscription_time(message.from_user.id)}")

@bot.message_handler(commands=['gift'])
async def gift_subscription(message):
    if message.from_user.id != OWNER_ID:
        await bot.reply_to(message, "❌ للأونر فقط @Dwojj")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await bot.reply_to(message, "/gift [ايدي] [مدة]\nمثال: /gift 8619852744 5 دقائق")
        return
    try:
        target_id = int(args[1])
        hours = parse_duration(args[2])
        if hours:
            add_subscription(target_id, hours)
            await bot.reply_to(message, f"✅ تم تفعيل اشتراك {target_id} لمدة {args[2]}")
            try:
                await bot.send_message(target_id, f"🎁 تم تفعيل اشتراك لك لمدة {args[2]} بواسطة الأونر @Dwojj")
            except:
                pass
    except:
        await bot.reply_to(message, "❌ خطأ")

@bot.message_handler(commands=['login'])
async def login(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ اشتراك مطلوب: /subscribe")
        return
    if is_verified(user_id):
        await bot.reply_to(message, "✅ مسجل بالفعل")
        return
    user_steps[user_id] = {"step": "waiting_phone"}
    await bot.reply_to(message, "📱 أرسل رقمك مع +\nمثال: +966512345678")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_phone")
async def handle_phone(message):
    user_id = message.from_user.id
    phone = message.text.strip()
    if not phone.startswith('+'):
        await bot.reply_to(message, "❌ الرقم يبدأ بـ +")
        return
    await bot.reply_to(message, "⏳ جاري إرسال الكود...")
    result = await send_code_telethon(user_id, phone)
    if result is True:
        user_steps[user_id] = {"step": "waiting_code"}
        await bot.reply_to(message, "✅ تم إرسال الكود\nأدخل الكود بمسافات:\nمثال: 1 2 3 4 5")
    else:
        await bot.reply_to(message, f"❌ فشل: {result}")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_code")
async def handle_code(message):
    user_id = message.from_user.id
    code = message.text.strip().replace(" ", "")
    if not code.isdigit():
        await bot.reply_to(message, "❌ الكود أرقام فقط")
        return
    result = await verify_code_telethon(user_id, code)
    if result is True:
        del user_steps[user_id]
        await bot.reply_to(message, "✅ تم الدخول\n/takleesh\n/tasteer")
    elif result == "password_needed":
        user_steps[user_id] = {"step": "waiting_password"}
        await bot.reply_to(message, "🔐 أرسل كلمة المرور:")
    else:
        await bot.reply_to(message, "❌ كود خطأ")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_password")
async def handle_password(message):
    user_id = message.from_user.id
    password = message.text.strip()
    result = await verify_password_telethon(user_id, password)
    if result is True:
        del user_steps[user_id]
        await bot.reply_to(message, "✅ تم الدخول")
    else:
        await bot.reply_to(message, "❌ كلمة مرور خطأ")
        del user_steps[user_id]

@bot.message_handler(commands=['takleesh'])
async def takleesh(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ اشتراك مطلوب: /subscribe")
        return
    if not is_verified(user_id):
        await bot.reply_to(message, "❌ سجل دخول: /login")
        return
    if user_id in active_spams:
        await bot.reply_to(message, "⚠️ عملية شغالة: /stop")
        return
    user_steps[user_id] = {"step": "takleesh_target"}
    await bot.reply_to(message, "🎯 أرسل معرف المستهدف (@username أو ID):")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_target")
async def takleesh_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "takleesh_count", "target": target}
    await bot.reply_to(message, "🔢 كم رسالة تريد إرسالها؟ (التطفية التلقائية)")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_count")
async def takleesh_count(message):
    user_id = message.from_user.id
    try:
        count = int(message.text.strip())
        if count < 1:
            raise ValueError
    except:
        await bot.reply_to(message, "❌ عدد غير صالح")
        del user_steps[user_id]
        return
    target = user_steps[user_id]["target"]
    await bot.reply_to(message, f"⚡ بدء إرسال {count} كليشة طويلة جداً...")
    asyncio.create_task(send_takleesh_messages(user_id, target, count, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['tasteer'])
async def tasteer(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ اشتراك مطلوب: /subscribe")
        return
    if not is_verified(user_id):
        await bot.reply_to(message, "❌ سجل دخول: /login")
        return
    if user_id in active_spams:
        await bot.reply_to(message, "⚠️ عملية شغالة: /stop")
        return
    user_steps[user_id] = {"step": "tasteer_target"}
    await bot.reply_to(message, "🎯 أرسل معرف المستهدف (@username أو ID):")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_target")
async def tasteer_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "tasteer_lines", "target": target}
    await bot.reply_to(message, "🔢 كم سطر تريد إرسالها؟ (مثال: 5)")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_lines")
async def tasteer_lines(message):
    user_id = message.from_user.id
    try:
        lines = int(message.text.strip())
        if lines < 1:
            raise ValueError
    except:
        await bot.reply_to(message, "❌ عدد غير صالح")
        del user_steps[user_id]
        return
    user_steps[user_id] = {"step": "tasteer_delay", "target": user_steps[user_id]["target"], "lines": lines}
    await bot.reply_to(message, "⏱️ السرعة بين كل سطر (بالثواني):\nمثال: 2")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_delay")
async def tasteer_delay(message):
    user_id = message.from_user.id
    try:
        delay = float(message.text.strip())
        if delay < 0.5:
            raise ValueError
    except:
        await bot.reply_to(message, "❌ سرعة غير صالحة (أقل قيمة 0.5 ثانية)")
        del user_steps[user_id]
        return
    target = user_steps[user_id]["target"]
    lines = user_steps[user_id]["lines"]
    await bot.reply_to(message, f"🚀 بدء إرسال {lines} سطر تسطير بفاصل {delay} ثانية")
    asyncio.create_task(send_tasteer_messages(user_id, target, lines, delay, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['stop'])
async def stop(message):
    user_id = message.from_user.id
    if user_id in active_spams:
        active_spams[user_id]["stop"] = True
        await bot.reply_to(message, "🛑 جاري إيقاف العملية...")
    else:
        await bot.reply_to(message, "⚠️ لا توجد عملية نشطة")

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Shadow Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

async def main():
    print("🔥 SHADOW BOT is running...")
    print("✅ كليشات طويلة جداً (اكثر من 50 كلمة)")
    print("✅ آلاف الكلمات السعودية القوية")
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())    c = conn.cursor()
    c.execute("SELECT expiry FROM subscriptions WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        expiry = datetime.fromisoformat(row[0])
        if datetime.now() < expiry:
            return True
        else:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
    return False

def add_subscription(user_id, duration_hours):
    user_id = str(user_id)
    expiry = datetime.now() + timedelta(hours=duration_hours)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)", (user_id, expiry.isoformat()))
    conn.commit()
    conn.close()

def get_subscription_time(user_id):
    user_id = str(user_id)
    if user_id == str(OWNER_ID):
        return "دائم (الأونر)"
    conn = sqlite3.connect(DB_PATH)
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
            return f"{hours} ساعة و {minutes} دقيقة متبقية"
        elif minutes > 0:
            return f"{minutes} دقيقة متبقية"
    return "غير مشترك"

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
add_subscription(OWNER_ID, 87600)

PREFIXES = ["لحلكك", "اشيلك", "عبالك", "انيجمك", "مصمص", "اهف", "اربطك", "اطحن", "اكهرب", "احط", "اقتحم", "اخدر", "انيج", "ربك", "اعبد"]
MIDDLES = ["الهالبك", "بعيري", "تيزمك", "علصدرك", "عيورتي", "بقياطين", "ضلوعك", "قضيبي", "نسلك", "زبي", "صريمك", "كسمك", "بكسختك", "براسك"]
SUFFIXES = ["يا ابن الكلب", "يا ابن الشرموطه", "يا ابن القحبه", "يا ديوث", "يا خنيث", "يا ابن المتناكه", "يا ابن العاهره", "يا خول", "يا جرار"]
STRONGS = ["كس امك", "كسمك", "كس اختك", "كسم امك", "انيك امك", "اطحن مخك"]

LONG_TAKLEESH_WORDS = [
    "لحلكك الهالبك طيزمك يا ابن الكلب انيك كس امك",
    "اشيلك بعيري يا ابن الشرموطه كس اختك يا ديوث",
    "عبالك اعوفك؟ اني المفروض انيك كس امك يا ابن القحبه",
    "انيجمك علصدرك يا ابن الزانيه واطحن مخك يا كلب",
    "مصمص عيورتي يا ابن العاهره واخليك تلحس جزمتي",
    "اهف اختك بطرف عيري يا ديوث واخليها شرموطه",
    "اربطك بقياطين قندرتي يا ابن الكحبه واسحبك",
    "اطحن ضلوعك يا ابن المتناكه واخلطها بالاسمنت",
    "اكهرب طيزك يا ابن الشرموطه واخليك تقفز",
    "احط قضيبي بكس امك يا ابن الدعاره قدام اهلك",
]

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

def generate_takleesh():
    parts = [random.choice(PREFIXES), random.choice(MIDDLES)]
    if random.random() > 0.5:
        parts.append(random.choice(STRONGS))
    parts.append(random.choice(SUFFIXES))
    return " ".join(parts)

async def send_takleesh_messages(user_id, target, count, chat_id):
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك")
        return
    if user_id in active_spams:
        active_spams[user_id]["stop"] = False
    else:
        active_spams[user_id] = {"stop": False}
    client = get_client(user_id)
    if not client:
        await bot.send_message(chat_id, "❌ خطأ في الجلسة")
        return
    for i in range(count):
        if active_spams[user_id]["stop"]:
            await bot.send_message(chat_id, "🛑 تم الإيقاف")
            break
        if random.random() < 0.6:
            word = random.choice(LONG_TAKLEESH_WORDS)
        else:
            word = generate_takleesh()
        try:
            await client.send_message(target, word)
        except Exception as e:
            await bot.send_message(chat_id, f"❌ فشل: {str(e)}")
            break
        await asyncio.sleep(1)
    await bot.send_message(chat_id, f"✅ تم إرسال {count} كليشة")
    if user_id in active_spams:
        del active_spams[user_id]

async def send_tasteer_messages(user_id, target, delay, chat_id):
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك")
        return
    if user_id in active_spams:
        active_spams[user_id]["stop"] = False
    else:
        active_spams[user_id] = {"stop": False}
    client = get_client(user_id)
    if not client:
        await bot.send_message(chat_id, "❌ خطأ في الجلسة")
        return
    tasteer_list = STRONGS + SUFFIXES + ["كس امك يا ابن القحبه", "كسمك يا شرموطه", "كس اختك يا ديوث", "انيك امك يا خنيث"]
    for i in range(3):
        if active_spams[user_id]["stop"]:
            await bot.send_message(chat_id, "🛑 تم الإيقاف")
            break
        word = random.choice(tasteer_list)
        try:
            await client.send_message(target, word)
        except Exception as e:
            await bot.send_message(chat_id, f"❌ فشل: {str(e)}")
            break
        await asyncio.sleep(delay)
    await bot.send_message(chat_id, "✅ تم الانتهاء")
    if user_id in active_spams:
        del active_spams[user_id]

@bot.message_handler(commands=['start'])
async def start(message):
    status = get_subscription_time(message.from_user.id)
    await bot.reply_to(message, f"🔥 فشار بوت 🔥\nالمبرمج: ايليا الملائكة\nالاونر: @Dwojj\nحالة الاشتراك: {status}\nاوامر: /login, /takleesh, /tasteer, /stop, /subscribe, /myplan")

@bot.message_handler(commands=['subscribe'])
async def subscribe(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⭐ ساعة - 15 نجمة", callback_data="sub_hour"),
        InlineKeyboardButton("⭐ يوم - 50 نجمة", callback_data="sub_day"),
        InlineKeyboardButton("⭐ اسبوع - 150 نجمة", callback_data="sub_week"),
        InlineKeyboardButton("⭐ شهر - 250 نجمة", callback_data="sub_month")
    )
    await bot.reply_to(message, "اختر مدة الاشتراك:", reply_markup=markup)

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
            description=f"⭐ {plan['stars']} نجمة - {plan['name']}",
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
    if "ساعة" in payload:
        add_subscription(user_id, 1)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة ساعة")
    elif "يوم" in payload:
        add_subscription(user_id, 24)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة يوم")
    elif "اسبوع" in payload:
        add_subscription(user_id, 168)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة اسبوع")
    elif "شهر" in payload:
        add_subscription(user_id, 720)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة شهر")

@bot.message_handler(commands=['myplan'])
async def myplan(message):
    await bot.reply_to(message, f"حالتك: {get_subscription_time(message.from_user.id)}")

@bot.message_handler(commands=['gift'])
async def gift_subscription(message):
    if message.from_user.id != OWNER_ID:
        await bot.reply_to(message, "للأونر فقط")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await bot.reply_to(message, "/gift [ايدي] [مدة]\nمثال: /gift 8619852744 5 دقائق")
        return
    try:
        target_id = int(args[1])
        hours = parse_duration(args[2])
        if hours:
            add_subscription(target_id, hours)
            await bot.reply_to(message, f"✅ تم تفعيل اشتراك {target_id} لمدة {args[2]}")
    except:
        await bot.reply_to(message, "خطأ")

@bot.message_handler(commands=['login'])
async def login(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "اشتراك مطلوب: /subscribe")
        return
    if is_verified(user_id):
        await bot.reply_to(message, "مسجل بالفعل")
        return
    user_steps[user_id] = {"step": "waiting_phone"}
    await bot.reply_to(message, "ارسل رقمك مع +\nمثال: +966512345678")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_phone")
async def handle_phone(message):
    user_id = message.from_user.id
    phone = message.text.strip()
    if not phone.startswith('+'):
        await bot.reply_to(message, "الرقم يبدأ بـ +")
        return
    await bot.reply_to(message, "جاري ارسال الكود...")
    result = await send_code_telethon(user_id, phone)
    if result is True:
        user_steps[user_id] = {"step": "waiting_code"}
        await bot.reply_to(message, "تم ارسال الكود\nادخل الكود بمسافات:\nمثال: 1 2 3 4 5")
    else:
        await bot.reply_to(message, f"فشل: {result}")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_code")
async def handle_code(message):
    user_id = message.from_user.id
    code = message.text.strip().replace(" ", "")
    if not code.isdigit():
        await bot.reply_to(message, "الكود ارقام فقط")
        return
    result = await verify_code_telethon(user_id, code)
    if result is True:
        del user_steps[user_id]
        await bot.reply_to(message, "✅ تم الدخول\n/takleesh\n/tasteer")
    elif result == "password_needed":
        user_steps[user_id] = {"step": "waiting_password"}
        await bot.reply_to(message, "ارسل كلمة المرور:")
    else:
        await bot.reply_to(message, "كود خطأ")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_password")
async def handle_password(message):
    user_id = message.from_user.id
    password = message.text.strip()
    result = await verify_password_telethon(user_id, password)
    if result is True:
        del user_steps[user_id]
        await bot.reply_to(message, "✅ تم الدخول")
    else:
        await bot.reply_to(message, "كلمة مرور خطأ")
        del user_steps[user_id]

@bot.message_handler(commands=['takleesh'])
async def takleesh(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "اشتراك مطلوب: /subscribe")
        return
    if not is_verified(user_id):
        await bot.reply_to(message, "سجل دخول: /login")
        return
    if user_id in active_spams:
        await bot.reply_to(message, "عملية شغالة: /stop")
        return
    user_steps[user_id] = {"step": "takleesh_target"}
    await bot.reply_to(message, "ارسل معرف المستهدف:")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_target")
async def takleesh_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "takleesh_count", "target": target}
    await bot.reply_to(message, "كم رسالة؟")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_count")
async def takleesh_count(message):
    user_id = message.from_user.id
    try:
        count = int(message.text.strip())
        if count < 1:
            raise ValueError
    except:
        await bot.reply_to(message, "عدد غير صالح")
        del user_steps[user_id]
        return
    target = user_steps[user_id]["target"]
    await bot.reply_to(message, f"بدء ارسال {count} كليشة")
    asyncio.create_task(send_takleesh_messages(user_id, target, count, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['tasteer'])
async def tasteer(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "اشتراك مطلوب: /subscribe")
        return
    if not is_verified(user_id):
        await bot.reply_to(message, "سجل دخول: /login")
        return
    if user_id in active_spams:
        await bot.reply_to(message, "عملية شغالة: /stop")
        return
    user_steps[user_id] = {"step": "tasteer_target"}
    await bot.reply_to(message, "ارسل معرف المستهدف:")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_target")
async def tasteer_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "tasteer_delay", "target": target}
    await bot.reply_to(message, "السرعة (ثانية):")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_delay")
async def tasteer_delay(message):
    user_id = message.from_user.id
    try:
        delay = float(message.text.strip())
        if delay < 0.5:
            raise ValueError
    except:
        await bot.reply_to(message, "سرعة غير صالحة")
        del user_steps[user_id]
        return
    target = user_steps[user_id]["target"]
    await bot.reply_to(message, f"بدء ارسال 3 اسطر")
    asyncio.create_task(send_tasteer_messages(user_id, target, delay, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['stop'])
async def stop(message):
    user_id = message.from_user.id
    if user_id in active_spams:
        active_spams[user_id]["stop"] = True
        await bot.reply_to(message, "جاري الايقاف")
    else:
        await bot.reply_to(message, "ما فيه عملية")

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Shadow Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

async def main():
    print("SHADOW BOT is running...")
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
