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
