import asyncio
import re
import random
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telebot.async_telebot import AsyncTeleBot

# =============== إعدادات API (من my.telegram.org) ===============
API_ID = 30324289
API_HASH = "93e20ced9ed0fa7e7e903900c11633d6"
BOT_TOKEN = "8817608659:AAF8O-I58x-khZLq4AzY-OWTyfgPIcNEo1M"

# =============== قاعدة بيانات ===============
user_sessions = {}  # {user_id: {"client": client, "step": str, "phone": str}}
active_spams = {}   # {user_id: {"stop": bool}}
user_steps = {}     # {user_id: {"step": str, "target": str, "count": int, "delay": float}}

# =============== كلمات التكليش ===============
TAKLEESH_WORDS = [
    "لحلكك الهالبك طيزمك", "اشيلك بعيري", "عبالك اعوفك؟", "انيجمك علصدرك", "ابن الزانيه",
    "مصمص عيورتي", "اهف اختك بطرف عيري", "اربطك بقياطين قندرتي", "اشيل ربك واركعه بلكاع",
    "ابن الكحبه الستشرافيه", "اطحن ضلوعك", "اكهرب طيزك", "احط قضيبي بكس امك", "اسوي كسيسمك طشار",
    "اقتحم نسلك", "ادحس عيري بكسمك", "اخدر امك", "انيج امك الكحبه", "ربك اسمطه", "اعبد زبي",
    "المخنث", "اصعق صريمك", "احط الدروب بطيزك", "اطشر صريمك", "انيج اختك البربوك", "افلشك تفليش",
    "اذب تيزاب بكسمك", "افرش كسمك", "انيج رب ربك", "افترس طيزك", "اخدر طيزختك", "اضربمك",
    "انيجمك فرنسي", "اخرمش طيزك", "العب بوبجي بكسمك", "الفيمبوي", "اتنايج وي اهلك"
]

# =============== كلمات التسطير ===============
TASTEER_WORDS = [
    "القحاب", "يا اخو الشرموطه", "يا ابن الوسيعه", "يا ديوث", "يا ابن القحبه",
    "يا خنيث", "الخنيث", "يا ابن الديوث", "يا ابن الزب", "اصمل بنيك", "عار امك",
    "يا مخنث", "يا ابن الكس", "يا ابن الهايته", "يا حمار", "يا فحل اختك",
    "يا كس امك", "يا زب الكلب", "يا ابن المتناكه"
]

# =============== بوت التحكم ===============
bot = AsyncTeleBot(BOT_TOKEN)

# =============== دوال Telethon ===============
async def send_code(user_id, phone):
    """إرسال كود التفعيل إلى حساب المستخدم على تليجرام"""
    client = TelegramClient(f"sessions/user_{user_id}", API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        try:
            await client.send_code_request(phone)
            user_sessions[user_id] = {"client": client, "phone": phone, "step": "waiting_code"}
            return True
        except Exception as e:
            return str(e)
    else:
        user_sessions[user_id] = {"client": client, "phone": phone, "step": "ready"}
        return True

async def verify_code(user_id, code):
    """التحقق من الكود"""
    data = user_sessions.get(user_id)
    if not data or data["step"] != "waiting_code":
        return False
    
    client = data["client"]
    phone = data["phone"]
    
    try:
        await client.sign_in(phone, code)
        user_sessions[user_id]["step"] = "ready"
        return True
    except SessionPasswordNeededError:
        user_sessions[user_id]["step"] = "waiting_password"
        return "password_needed"
    except Exception as e:
        return str(e)

async def verify_password(user_id, password):
    """إذا كان الحساب مفعل بخطوتين"""
    data = user_sessions.get(user_id)
    if not data or data["step"] != "waiting_password":
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

# =============== دوال الإرسال ===============
async def send_takleesh_messages(user_id, target, count, chat_id):
    """إرسال كلايش من حساب المستخدم"""
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
            await bot.send_message(chat_id, "🛑 تم إيقاف التكليش")
            break
        
        word = random.choice(TAKLEESH_WORDS)
        try:
            await client.send_message(target, word)
        except Exception as e:
            await bot.send_message(chat_id, f"❌ فشل الإرسال: {str(e)}")
            break
        
        await asyncio.sleep(1)
    
    await bot.send_message(chat_id, f"✅ تم إرسال {count} كليشة")
    if user_id in active_spams:
        del active_spams[user_id]

async def send_tasteer_messages(user_id, target, delay, chat_id):
    """إرسال تسطير من حساب المستخدم"""
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
            await bot.send_message(chat_id, "🛑 تم إيقاف التسطير")
            break
        
        word = random.choice(TASTEER_WORDS)
        try:
            await client.send_message(target, word)
        except Exception as e:
            await bot.send_message(chat_id, f"❌ فشل الإرسال: {str(e)}")
            break
        
        await asyncio.sleep(delay)
    
    await bot.send_message(chat_id, "✅ تم الانتهاء من التسطير")
    if user_id in active_spams:
        del active_spams[user_id]

# =============== أوامر البوت ===============
@bot.message_handler(commands=['start'])
async def start(message):
    user_id = message.from_user.id
    if is_verified(user_id):
        await bot.reply_to(message, "✅ أنت مسجل الدخول\n/takleesh - تكليش\n/tasteer - تسطير\n/stop - إيقاف")
    else:
        await bot.reply_to(message, "🔐 مرحباً\nاستخدم /login")

@bot.message_handler(commands=['login'])
async def login(message):
    user_id = message.from_user.id
    if is_verified(user_id):
        await bot.reply_to(message, "✅ مسجل بالفعل")
        return
    
    user_steps[user_id] = {"step": "waiting_phone"}
    await bot.reply_to(message, "📱 أرسل رقمك مع رمز البلد\nمثال: +9647701234567")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_phone")
async def handle_phone(message):
    user_id = message.from_user.id
    phone = message.text.strip()
    
    if not phone.startswith('+'):
        await bot.reply_to(message, "❌ الرقم يجب أن يبدأ بـ +\nمثال: +9647701234567")
        return
    
    await bot.reply_to(message, "⏳ جاري إرسال الكود...")
    
    result = await send_code(user_id, phone)
    if result is True:
        user_steps[user_id] = {"step": "waiting_code"}
        await bot.reply_to(message, "✅ تم إرسال الكود إلى تليجرام\nأدخل الكود (بدون مسافات):")
    else:
        await bot.reply_to(message, f"❌ فشل: {result}")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_code")
async def handle_code(message):
    user_id = message.from_user.id
    code = message.text.strip().replace(" ", "")
    
    result = await verify_code(user_id, code)
    if result is True:
        del user_steps[user_id]
        await bot.reply_to(message, "✅ تم تسجيل الدخول\n/takleesh - تكليش\n/tasteer - تسطير")
    elif result == "password_needed":
        user_steps[user_id] = {"step": "waiting_password"}
        await bot.reply_to(message, "🔐 حسابك مفعل بخطوتين\nأرسل كلمة المرور:")
    else:
        await bot.reply_to(message, f"❌ كود خطأ: {result}")
        del user_steps[user_id]

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "waiting_password")
async def handle_password(message):
    user_id = message.from_user.id
    password = message.text.strip()
    
    result = await verify_password(user_id, password)
    if result is True:
        del user_steps[user_id]
        await bot.reply_to(message, "✅ تم تسجيل الدخول\n/takleesh - تكليش\n/tasteer - تسطير")
    else:
        await bot.reply_to(message, f"❌ كلمة مرور خطأ: {result}")
        del user_steps[user_id]

@bot.message_handler(commands=['takleesh'])
async def takleesh(message):
    user_id = message.from_user.id
    
    if not is_verified(user_id):
        await bot.reply_to(message, "❌ سجل دخول أولاً: /login")
        return
    
    if user_id in active_spams:
        await bot.reply_to(message, "⚠️ فيه عملية شغالة استخدم /stop")
        return
    
    user_steps[user_id] = {"step": "takleesh_target"}
    await bot.reply_to(message, "🎯 أرسل معرف المستخدم المستهدف:\n@username أو ID")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "takleesh_target")
async def takleesh_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "takleesh_count", "target": target}
    await bot.reply_to(message, "🔢 كم رسالة تبغى ترسل؟")

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
    await bot.reply_to(message, f"⚡ بدء إرسال {count} كليشة...")
    
    asyncio.create_task(send_takleesh_messages(user_id, target, count, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['tasteer'])
async def tasteer(message):
    user_id = message.from_user.id
    
    if not is_verified(user_id):
        await bot.reply_to(message, "❌ سجل دخول أولاً: /login")
        return
    
    if user_id in active_spams:
        await bot.reply_to(message, "⚠️ فيه عملية شغالة استخدم /stop")
        return
    
    user_steps[user_id] = {"step": "tasteer_target"}
    await bot.reply_to(message, "🎯 أرسل معرف المستخدم المستهدف")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_target")
async def tasteer_target(message):
    user_id = message.from_user.id
    target = message.text.strip()
    user_steps[user_id] = {"step": "tasteer_delay", "target": target}
    await bot.reply_to(message, "⏱️ السرعة بين كل سطر (ثانية):\nمثال: 3")

@bot.message_handler(func=lambda m: user_steps.get(m.from_user.id, {}).get("step") == "tasteer_delay")
async def tasteer_delay(message):
    user_id = message.from_user.id
    try:
        delay = float(message.text.strip())
        if delay < 0.5:
            raise ValueError
    except:
        await bot.reply_to(message, "❌ سرعة غير صالحة (أقل قيمة 0.5)")
        del user_steps[user_id]
        return
    
    target = user_steps[user_id]["target"]
    await bot.reply_to(message, f"🚀 بدء إرسال 3 أسطر بفاصل {delay} ثانية")
    
    asyncio.create_task(send_tasteer_messages(user_id, target, delay, message.chat.id))
    del user_steps[user_id]

@bot.message_handler(commands=['stop'])
async def stop(message):
    user_id = message.from_user.id
    if user_id in active_spams:
        active_spams[user_id]["stop"] = True
        await bot.reply_to(message, "🛑 جاري الإيقاف...")
    else:
        await bot.reply_to(message, "⚠️ ما فيه عملية شغالة")

# =============== تشغيل البوت ===============
async def main():
    print("🔥 SHADOW BOT with Telethon is running...")
    print("✅ المستخدم يسجل دخول ويستلم كود على تليجرام نفسه")
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
