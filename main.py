import asyncio
import re
import random
import os
import threading
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telebot.async_telebot import AsyncTeleBot
from flask import Flask

# =============== إعدادات API الجديدة ===============
API_ID = 30874435
API_HASH = "cc3b98786456de26fe5e803910051cea"
BOT_TOKEN = "8817608659:AAF8O-I58x-khZLq4AzY-OWTyfgPIcNEo1M"

user_sessions = {}
active_spams = {}
user_steps = {}

TAKLEESH_WORDS = [
    "لحلكك الهالبك طيزمك", "اشيلك بعيري", "عبالك اعوفك؟", "انيجمك علصدرك",
    "مصمص عيورتي", "اهف اختك بطرف عيري"
]

TASTEER_WORDS = [
    "القحاب", "يا خنيث", "يا ديوث", "الخنيث", "يا ابن الديوث"
]

bot = AsyncTeleBot(BOT_TOKEN)

async def send_code_telethon(user_id, phone):
    try:
        client = TelegramClient(f":memory:", API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            user_sessions[user_id] = {
                "client": client,
                "phone": phone,
                "step": "waiting_code"
            }
            return True
        else:
            user_sessions[user_id] = {
                "client": client,
                "phone": phone,
                "step": "ready"
            }
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
        word = random.choice(TAKLEESH_WORDS)
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
    if user_id in active_spams:
        active_spams[user_id]["stop"] = False
    else:
        active_spams[user_id] = {"stop": False}
    client = get_client(user_id)
    if not client:
        await bot.send_message(chat_id, "❌ خطأ في الجلسة")
        return
    for i in range(3):
        if active_spams[user_id]["stop"]:
            await bot.send_message(chat_id, "🛑 تم الإيقاف")
            break
        word = random.choice(TASTEER_WORDS)
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
    user_id = message.from_user.id
    if is_verified(user_id):
        await bot.reply_to(message, "✅ مسجل دخول\n/takleesh\n/tasteer\n/stop")
    else:
        await bot.reply_to(message, "🔐 استخدم /login")

@bot.message_handler(commands=['login'])
async def login(message):
    user_id = message.from_user.id
    if is_verified(user_id):
        await bot.reply_to(message, "✅ مسجل بالفعل")
        return
    user_steps[user_id] = {"step": "waiting_phone"}
    await bot.reply_to(message, "📱 أرسل رقمك مع +\nمثال: +9647701234567")

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
        await bot.reply_to(message, "❌ الكود أرقام فقط\nمثال: 1 2 3 4 5")
        return
    result = await verify_code_telethon(user_id, code)
    if result is True:
        del user_steps[user_id]
        await bot.reply_to(message, "✅ تم الدخول\n/takleesh\n/tasteer")
    elif result == "password_needed":
        user_steps[user_id] = {"step": "waiting_password"}
        await bot.reply_to(message, "🔐 أرسل كلمة المرور:")
    else:
        await bot.reply_to(message, f"❌ كود خطأ: {result}")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_password")
async def handle_password(message):
    user_id = message.from_user.id
    password = message.text.strip()
    result = await verify_password_telethon(user_id, password)
    if result is True:
        del user_steps[user_id]
        await bot.reply_to(message, "✅ تم الدخول\n/takleesh\n/tasteer")
    else:
        await bot.reply_to(message, f"❌ كلمة مرور خطأ: {result}")
        del user_steps[user_id]

@bot.message_handler(commands=['takleesh'])
async def takleesh(message):
    user_id = message.from_user.id
    if not is_verified(user_id):
        await bot.reply_to(message, "❌ سجل دخول: /login")
        return
    if user_id in active_spams:
        await bot.reply_to(message, "⚠️ عملية شغالة: /stop")
        return
    user_steps[user_id] = {"step": "takleesh_target"}
    await bot.reply_to(message, "🎯 أرسل معرف المستخدم:")

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
    if not is_verified(user_id):
        await bot.reply_to(message, "❌ سجل دخول: /login")
        return
    if user_id in active_spams:
        await bot.reply_to(message, "⚠️ عملية شغالة: /stop")
        return
    user_steps[user_id] = {"step": "tasteer_target"}
    await bot.reply_to(message, "🎯 أرسل معرف المستخدم:")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_target")
async def tasteer_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "tasteer_delay", "target": target}
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
    await bot.reply_to(message, f"🚀 بدء إرسال 3 أسطر")
    asyncio.create_task(send_tasteer_messages(user_id, target, delay, message.chat.id))
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
    print("🔥 SHADOW BOT with Telethon is running...")
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
