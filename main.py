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
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

API_ID = 30874435
API_HASH = "cc3b98786456de26fe5e803910051cea"
BOT_TOKEN = "8817608659:AAF8O-I58x-khZLq4AzY-OWTyfgPIcNEo1M"

OWNER_ID = 8603631953

user_sessions = {}
active_spams = {}
user_steps = {}

# =============== قاعدة بيانات SQLite ===============
DB_PATH = "subscriptions.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (user_id TEXT PRIMARY KEY, expiry TEXT)''')
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
    c.execute("INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)",
              (user_id, expiry.isoformat()))
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
        if hours > 0:
            return f"{hours} ساعة متبقية"
    return "غير مشترك"

init_db()

# الأونر مشترك تلقائياً
add_subscription(OWNER_ID, 87600)  # 10 سنوات

# =============== كلمات التكليش ===============
TAKLEESH_WORDS = [
    "لحلكك الهالبك طيزمك", "اشيلك بعيري", "عبالك اعوفك؟", "انيجمك علصدرك", "ابن الزانيه",
    "مصمص عيورتي", "اهف اختك بطرف عيري", "اربطك بقياطين قندرتي", "اشيل ربك واركعه بلكاع",
    "ابن الكحبه الستشرافيه", "اطحن ضلوعك", "اكهرب طيزك", "احط قضيبي بكس امك", "اسوي كسيسمك طشار",
    "اقتحم نسلك", "ادحس عيري بكسمك", "اخدر امك", "انيج امك الكحبه", "ربك اسمطه", "اعبد زبي",
    "المخنث", "اصعق صريمك", "احط الدروب بطيزك", "اطشر صريمك", "انيج اختك البربوك", "افلشك تفليش",
    "اذب تيزاب بكسمك", "افرش كسمك", "انيج رب ربك", "افترس طيزك", "اخدر طيزختك", "اضربمك",
    "انيجمك فرنسي", "اخرمش طيزك", "العب بوبجي بكسمك", "الفيمبوي", "اتنايج وي اهلك", "ادك كسمك"
]

TASTEER_WORDS = [
    "ابن العاهره", "يا ابن القحبه", "يا ابن الدعاره", "كس ام اهلك", "كسم امك", "يا ديوث", "يا جرار",
    "يا فحل اختك", "يا فحل امك", "انيك امك", "يا خنيث", "يا ابن الساقطه", "يا فحل خواتك",
    "يا ابن المتناكه", "يا شرمطه", "يا عاهر", "يا خول", "يا قواد", "يا منيوك"
]

bot = AsyncTeleBot(BOT_TOKEN)

# =============== دوال Telethon ===============
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
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
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
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
        return
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

# =============== أوامر البوت ===============
@bot.message_handler(commands=['start'])
async def start(message):
    user_id = message.from_user.id
    status = get_subscription_time(user_id)
    
    welcome_text = f"""
<b>🔥 بوت فـشـار 🔥</b>

━━━━━━━━━━━━━━━━━━━━
<b>🤖 المبرمج:</b> <i>الداهية ايليا الملائكة</i>
<b>👑 الاونر:</b> <i>@Dwojj</i>
━━━━━━━━━━━━━━━━━━━━

<b>📊 حالة الاشتراك:</b> {status}

<b>⚡ الأوامر المتاحة:</b>
• /login - تسجيل الدخول بحسابك
• /takleesh - بدء التكليش
• /tasteer - بدء التسطير
• /stop - إيقاف العملية
• /subscribe - الاشتراك بالبوت
• /myplan - معرفة باقي اشتراكك

━━━━━━━━━━━━━━━━━━━━
"""
    await bot.reply_to(message, welcome_text, parse_mode="HTML")

@bot.message_handler(commands=['subscribe'])
async def subscribe(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⭐ ساعة - 15 نجمة", callback_data="sub_hour"),
        InlineKeyboardButton("⭐ يوم - 50 نجمة", callback_data="sub_day"),
        InlineKeyboardButton("⭐ أسبوع - 150 نجمة", callback_data="sub_week"),
        InlineKeyboardButton("⭐ شهر - 250 نجمة", callback_data="sub_month")
    )
    await bot.reply_to(message, "⭐ اختر مدة الاشتراك:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
async def handle_subscription(call):
    data = call.data
    
    plans = {
        "sub_hour": {"stars": 15, "hours": 1, "name": "ساعة"},
        "sub_day": {"stars": 50, "hours": 24, "name": "يوم"},
        "sub_week": {"stars": 150, "hours": 168, "name": "أسبوع"},
        "sub_month": {"stars": 250, "hours": 720, "name": "شهر"}
    }
    
    if data in plans:
        plan = plans[data]
        await bot.answer_callback_query(call.id)
        
        await bot.send_invoice(
            chat_id=call.message.chat.id,
            title=f"اشتراك {plan['name']} - فشار بوت",
            description=f"تفعيل اشتراك {plan['name']} في بوت فشار\nيمكنك استخدام جميع الميزات",
            payload=f"sub_{plan['name']}",
            provider_token="",
            currency="XTR",
            prices=[{"label": f"⭐ {plan['name']}", "amount": plan['stars']}],
            need_name=False,
            need_phone_number=False,
            need_email=False
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
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة ساعة واحدة")
    elif "يوم" in payload:
        add_subscription(user_id, 24)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة يوم واحد")
    elif "أسبوع" in payload:
        add_subscription(user_id, 168)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة أسبوع")
    elif "شهر" in payload:
        add_subscription(user_id, 720)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة شهر")

@bot.message_handler(commands=['myplan'])
async def myplan(message):
    user_id = message.from_user.id
    status = get_subscription_time(user_id)
    await bot.reply_to(message, f"📊 حالة اشتراكك: {status}")

@bot.message_handler(commands=['gift'])
async def gift_subscription(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        await bot.reply_to(message, "❌ هذا الأمر خاص بالأونر فقط")
        return
    
    args = message.text.split()
    if len(args) != 3:
        await bot.reply_to(message, "❌ الاستخدام:\n/gift [ايدي المستخدم] [عدد الساعات]\n\nمثال:\n/gift 8619852744 720")
        return
    
    try:
        target_id = int(args[1])
        hours = int(args[2])
        add_subscription(target_id, hours)
        await bot.reply_to(message, f"✅ تم تفعيل اشتراك للمستخدم {target_id} لمدة {hours} ساعة")
        
        try:
            await bot.send_message(target_id, f"🎁 تم تفعيل اشتراك لك لمدة {hours} ساعة بواسطة الأونر @Dwojj")
        except:
            pass
    except:
        await bot.reply_to(message, "❌ تأكد من كتابة ايدي صحيح وعدد ساعات صحيح")

@bot.message_handler(commands=['login'])
async def login(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
        return
    if is_verified(user_id):
        await bot.reply_to(message, "✅ أنت مسجل بالفعل")
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
        await bot.reply_to(message, f"❌ كود خطأ")
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
        await bot.reply_to(message, f"❌ كلمة مرور خطأ")
        del user_steps[user_id]

@bot.message_handler(commands=['takleesh'])
async def takleesh(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe")
        return
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
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe")
        return
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
    print("🔥 SHADOW BOT is running...")
    threading.Thread(target=run_flask, daemon=True).start()
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())subscriptions = load_subscriptions()

# الأونر مشترك تلقائياً
subscriptions[str(OWNER_ID)] = (datetime.now() + timedelta(days=3650)).isoformat()
save_subscriptions(subscriptions)

def is_subscribed(user_id):
    user_id = str(user_id)
    # الأونر دائماً مشترك
    if user_id == str(OWNER_ID):
        return True
    if user_id in subscriptions:
        expiry = subscriptions[user_id]
        if datetime.now() < datetime.fromisoformat(expiry):
            return True
        else:
            del subscriptions[user_id]
            save_subscriptions(subscriptions)
    return False

def add_subscription(user_id, duration_hours):
    user_id = str(user_id)
    expiry = datetime.now() + timedelta(hours=duration_hours)
    subscriptions[user_id] = expiry.isoformat()
    save_subscriptions(subscriptions)

# =============== كلمات التكليش ===============
TAKLEESH_WORDS = [
    "لحلكك الهالبك طيزمك", "اشيلك بعيري", "عبالك اعوفك؟", "انيجمك علصدرك", "ابن الزانيه",
    "مصمص عيورتي", "اهف اختك بطرف عيري", "اربطك بقياطين قندرتي", "اشيل ربك واركعه بلكاع",
    "ابن الكحبه الستشرافيه", "اطحن ضلوعك", "اكهرب طيزك", "احط قضيبي بكس امك", "اسوي كسيسمك طشار",
    "اقتحم نسلك", "ادحس عيري بكسمك", "اخدر امك", "انيج امك الكحبه", "ربك اسمطه", "اعبد زبي",
    "المخنث", "اصعق صريمك", "احط الدروب بطيزك", "اطشر صريمك", "انيج اختك البربوك", "افلشك تفليش",
    "اذب تيزاب بكسمك", "افرش كسمك", "انيج رب ربك", "افترس طيزك", "اخدر طيزختك", "اضربمك",
    "انيجمك فرنسي", "اخرمش طيزك", "العب بوبجي بكسمك", "الفيمبوي", "اتنايج وي اهلك", "ادك كسمك",
    "ابن الكحبه اليوم", "اشوي على كسمك العير", "ادحسه بكسختك", "ايوي صريم امك", "طشار انيج عرضك",
    "عيري براسك", "ولك شبيك خفت", "اخضع لجباتي الحاره", "اعجن عيورتي بكسمك", "اخضع العيري",
    "استرجل", "اشكه لكسمك وعلي", "ادحس الكعبه بطيزك", "ابن الكحبه الرومانيه", "ابن القندره",
    "ازورك وجهك بعيري", "فرخي", "اصابعي تفترسك", "اختك كحبتي", "اله اشكه لحلكك", "انزل لعنه عيري بكسمك",
    "شو دتعال", "ابن المتبربكه", "ابن عاشقه العير", "دشوف شراح اسوي", "اتفل بصرمك", "احط عيورتي بطيزمك",
    "وعلي ماتكدرلي", "ادحس رجلي بكس اختك", "ولك تعال مصعيري", "انكز على صريمك", "اشنقك بلباس امك",
    "احط امك بطيزك", "ابن الهايته", "ابن الانحطاطيه", "امك احطها بعيري", "ابن الربل", "ابن مصاصه عيورتي",
    "ابن الناسوخيه", "اتناطح وي عنابه امك", "اله البك طيزمك", "اصعد على ضهرك", "نياج اختك اني",
    "ادحس البنكه بصرمك", "ابعبص صريمك", "افلش كسمك تفليش", "احط الويسكي بكس اختك", "اتسودن عليك",
    "ابن كحباتي", "اشلع شفايف امك", "اجنكل طيز اختك", "ابن بلاعت العير", "اجك امك بعيري", "امصمص ديوس اختك",
    "ابن المراهقه", "ابن التحب عيورتي", "اهف راس امك بل طاوه", "اشكشك ديوسك", "اربطك بقياطين قندرتي",
    "ابن الاسحاقيه", "ابن الانزلاقيه", "احط العرك بكس امك", "اكهرب طيزك", "فحلمك اني", "حدث",
    "ابن الدبل", "ابن الفريخه", "ابن جبتي الحاره", "اطشر مخك بعيري", "ابن الكحيبه", "افلش كسمك بوكسات",
    "اعوج ركبت امك", "ابن الزنا", "اهينك بعيري", "اسوي كسيسمك طشار", "اجب بلباس اختك", "اذب تيزاب بكسمك",
    "اصمل ولك", "اسد كس امك", "ابن سير النعال", "ابن الحوله", "ابن زبوبتي", "اخلي تمص جبتي", "كليشتي بكسمك",
    "اخلي عيري براسك", "دمبك العير", "اسوي طويزك وصلتين", "امصمص نهود امك", "اخلي تمص جبتي", "اعبد زبي",
    "وين تكدر لعيري", "امد تيل بصرمك", "اطب بين زرورك", "ابن ام العيوره", "انزل غضب الله بطيزك",
    "اشلع راس اختك", "اتفل بصرمك", "اقتحم نسلك", "ارعن", "انكز على صريمك", "اخدر امك"
]

# =============== كلمات التسطير (سعودية) ===============
TASTEER_WORDS = [
    "ابن العاهره", "يا ابن القحبه", "يا ابن الدعاره", "كس ام اهلك", "كسم امك", "يا ديوث", "يا جرار",
    "يا فحل اختك", "يا فحل امك", "انيك امك", "كسس اهلك", "مسوي تسوي قوي صح", "يا خنيث", "وش بك انيك أمك",
    "يا ابن الساقطه", "يا فحل خواتك", "شو بك كس امك", "مسوي تسوي غبي صح", "يا ديوث يا جرار",
    "يا ابن المتناكه", "يا شرمطه", "يا عاهر", "يا خول", "يا قواد", "يا منيوك", "يا ابن الحزانه",
    "يا وسخ", "يا جربان", "يا نجس", "يا رجس", "يا منفوح", "يا معفن", "يا خبيث", "يا رذيل",
    "يا حقير", "يا دنيء", "يا فاسق", "يا فاجر", "يا ملوث", "يا زب الكلب", "يا ابن الكلب",
    "يا ابن الحمار", "يا ابن البقره", "يا تيس", "يا حمار", "يا كلب", "يا خنزير", "يا قرد"
]

bot = AsyncTeleBot(BOT_TOKEN)

# =============== دوال Telethon ===============
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
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
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
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
        return
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

# =============== أوامر البوت ===============
@bot.message_handler(commands=['start'])
async def start(message):
    user_id = message.from_user.id
    subscribed = is_subscribed(user_id)
    status = "✅ مفعل" if subscribed else "❌ غير مفعل"
    
    welcome_text = f"""
<b>🔥 بوت فـشـار 🔥</b>

━━━━━━━━━━━━━━━━━━━━
<b>🤖 المبرمج:</b> <i>الداهية ايليا الملائكة</i>
<b>👑 الاونر:</b> <i>@Dwojj</i>
━━━━━━━━━━━━━━━━━━━━

<b>📊 حالة الاشتراك:</b> {status}

<b>⚡ الأوامر المتاحة:</b>
• /login - تسجيل الدخول بحسابك
• /takleesh - بدء التكليش
• /tasteer - بدء التسطير
• /stop - إيقاف العملية
• /subscribe - الاشتراك بالبوت
• /myplan - معرفة باقي اشتراكك

━━━━━━━━━━━━━━━━━━━━
<i>البوّاب اللي يفتح لك أبواب العيور</i>
"""
    await bot.reply_to(message, welcome_text, parse_mode="HTML")

@bot.message_handler(commands=['subscribe'])
async def subscribe(message):
    user_id = message.from_user.id
    if is_subscribed(user_id):
        await bot.reply_to(message, "✅ أنت مشترك بالفعل!")
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⭐ ساعة - 15 نجمة", callback_data="sub_hour"),
        InlineKeyboardButton("⭐ يوم - 50 نجمة", callback_data="sub_day"),
        InlineKeyboardButton("⭐ أسبوع - 150 نجمة", callback_data="sub_week"),
        InlineKeyboardButton("⭐ شهر - 250 نجمة", callback_data="sub_month")
    )
    
    await bot.reply_to(message, "⭐ اختر مدة الاشتراك:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
async def handle_subscription(call):
    user_id = call.from_user.id
    data = call.data
    
    prices = {
        "sub_hour": {"stars": 15, "hours": 1, "name": "ساعة"},
        "sub_day": {"stars": 50, "hours": 24, "name": "يوم"},
        "sub_week": {"stars": 150, "hours": 168, "name": "أسبوع"},
        "sub_month": {"stars": 250, "hours": 720, "name": "شهر"}
    }
    
    if data in prices:
        price = prices[data]
        await bot.answer_callback_query(call.id)
        
        # إرسال فاتورة النجوم
        await bot.send_invoice(
            chat_id=call.message.chat.id,
            title=f"اشتراك {price['name']}",
            description=f"تفعيل اشتراك {price['name']} في بوت فشار",
            payload=f"sub_{price['name']}",
            provider_token="",
            currency="XTR",
            prices=[{"label": f"{price['name']}", "amount": price['stars']}],
            need_name=False,
            need_phone_number=False,
            need_email=False
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
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة ساعة واحدة")
    elif "يوم" in payload:
        add_subscription(user_id, 24)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة يوم واحد")
    elif "أسبوع" in payload:
        add_subscription(user_id, 168)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة أسبوع")
    elif "شهر" in payload:
        add_subscription(user_id, 720)
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة شهر")

@bot.message_handler(commands=['myplan'])
async def myplan(message):
    user_id = str(message.from_user.id)
    if user_id == str(OWNER_ID):
        await bot.reply_to(message, "👑 أنت الأونر، لديك صلاحية دائمة")
        return
    if user_id in subscriptions:
        expiry = subscriptions[user_id]
        remaining = datetime.fromisoformat(expiry) - datetime.now()
        hours = int(remaining.total_seconds() // 3600)
        if hours > 0:
            await bot.reply_to(message, f"✅ اشتراكك فعال لمدة {hours} ساعة متبقية")
        else:
            await bot.reply_to(message, "❌ اشتراكك انتهى\nاستخدم /subscribe لتجديد")
    else:
        await bot.reply_to(message, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")

# أمر خاص بالاونر فقط - يعطي اشتراك لأي مستخدم
@bot.message_handler(commands=['gift'])
async def gift_subscription(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        await bot.reply_to(message, "❌ هذا الأمر خاص بالأونر فقط")
        return
    
    args = message.text.split()
    if len(args) != 3:
        await bot.reply_to(message, "❌ الاستخدام:\n/gift [ايدي المستخدم] [عدد الساعات]")
        return
    
    try:
        target_id = int(args[1])
        hours = int(args[2])
        add_subscription(target_id, hours)
        await bot.reply_to(message, f"✅ تم تفعيل اشتراك للمستخدم {target_id} لمدة {hours} ساعة")
        
        # إشعار للمستخدم
        try:
            await bot.send_message(target_id, f"🎁 تم تفعيل اشتراك لك لمدة {hours} ساعة بواسطة الأونر")
        except:
            pass
    except:
        await bot.reply_to(message, "❌ تأكد من كتابة ايدي صحيح وعدد ساعات صحيح")

@bot.message_handler(commands=['login'])
async def login(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
        return
    if is_verified(user_id):
        await bot.reply_to(message, "✅ أنت مسجل بالفعل")
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
        await bot.reply_to(message, f"❌ كود خطأ")
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
        await bot.reply_to(message, f"❌ كلمة مرور خطأ")
        del user_steps[user_id]

@bot.message_handler(commands=['takleesh'])
async def takleesh(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
        return
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
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
        return
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
def is_subscribed(user_id):
    user_id = str(user_id)
    if user_id in subscriptions:
        expiry = subscriptions[user_id]
        if datetime.now() < datetime.fromisoformat(expiry):
            return True
        else:
            del subscriptions[user_id]
            save_subscriptions(subscriptions)
    return False

def add_subscription(user_id, duration_hours):
    user_id = str(user_id)
    expiry = datetime.now() + timedelta(hours=duration_hours)
    subscriptions[user_id] = expiry.isoformat()
    save_subscriptions(subscriptions)

# =============== كلمات التكليش (لا نهائية) ===============
TAKLEESH_WORDS = [
    "لحلكك الهالبك طيزمك", "اشيلك بعيري", "عبالك اعوفك؟", "انيجمك علصدرك", "ابن الزانيه",
    "مصمص عيورتي", "اهف اختك بطرف عيري", "اربطك بقياطين قندرتي", "اشيل ربك واركعه بلكاع",
    "ابن الكحبه الستشرافيه", "اطحن ضلوعك", "اكهرب طيزك", "احط قضيبي بكس امك", "اسوي كسيسمك طشار",
    "اقتحم نسلك", "ادحس عيري بكسمك", "اخدر امك", "انيج امك الكحبه", "ربك اسمطه", "اعبد زبي",
    "المخنث", "اصعق صريمك", "احط الدروب بطيزك", "اطشر صريمك", "انيج اختك البربوك", "افلشك تفليش",
    "اذب تيزاب بكسمك", "افرش كسمك", "انيج رب ربك", "افترس طيزك", "اخدر طيزختك", "اضربمك",
    "انيجمك فرنسي", "اخرمش طيزك", "العب بوبجي بكسمك", "الفيمبوي", "اتنايج وي اهلك", "ادك كسمك",
    "ابن الكحبه اليوم", "اشوي على كسمك العير", "ادحسه بكسختك", "ايوي صريم امك", "طشار انيج عرضك",
    "عيري براسك", "ولك شبيك خفت", "اخضع لجباتي الحاره", "اعجن عيورتي بكسمك", "اخضع العيري",
    "استرجل", "اشكه لكسمك وعلي", "ادحس الكعبه بطيزك", "ابن الكحبه الرومانيه", "ابن القندره",
    "ازورك وجهك بعيري", "فرخي", "اصابعي تفترسك", "اختك كحبتي", "اله اشكه لحلكك", "انزل لعنه عيري بكسمك",
    "شو دتعال", "ابن المتبربكه", "ابن عاشقه العير", "دشوف شراح اسوي", "اتفل بصرمك", "احط عيورتي بطيزمك",
    "وعلي ماتكدرلي", "ادحس رجلي بكس اختك", "ولك تعال مصعيري", "انكز على صريمك", "اشنقك بلباس امك",
    "احط امك بطيزك", "ابن الهايته", "ابن الانحطاطيه", "امك احطها بعيري", "ابن الربل", "ابن مصاصه عيورتي",
    "ابن الناسوخيه", "اتناطح وي عنابه امك", "اله البك طيزمك", "اصعد على ضهرك", "نياج اختك اني",
    "ادحس البنكه بصرمك", "ابعبص صريمك", "افلش كسمك تفليش", "احط الويسكي بكس اختك", "اتسودن عليك",
    "ابن كحباتي", "اشلع شفايف امك", "اجنكل طيز اختك", "ابن بلاعت العير", "اجك امك بعيري", "امصمص ديوس اختك",
    "ابن المراهقه", "ابن التحب عيورتي", "اهف راس امك بل طاوه", "اشكشك ديوسك", "اربطك بقياطين قندرتي",
    "ابن الاسحاقيه", "ابن الانزلاقيه", "احط العرك بكس امك", "اكهرب طيزك", "فحلمك اني", "حدث",
    "ابن الدبل", "ابن الفريخه", "ابن جبتي الحاره", "اطشر مخك بعيري", "ابن الكحيبه", "افلش كسمك بوكسات",
    "اعوج ركبت امك", "ابن الزنا", "اهينك بعيري", "اسوي كسيسمك طشار", "اجب بلباس اختك", "اذب تيزاب بكسمك",
    "اصمل ولك", "اسد كس امك", "ابن سير النعال", "ابن الحوله", "ابن زبوبتي", "اخلي تمص جبتي", "كليشتي بكسمك",
    "اخلي عيري براسك", "دمبك العير", "اسوي طويزك وصلتين", "امصمص نهود امك", "اخلي تمص جبتي", "اعبد زبي",
    "وين تكدر لعيري", "امد تيل بصرمك", "اطب بين زرورك", "ابن ام العيوره", "انزل غضب الله بطيزك",
    "اشلع راس اختك", "اتفل بصرمك", "اقتحم نسلك", "ارعن", "انكز على صريمك", "اخدر امك"
]

# =============== كلمات التسطير (سعودية) ===============
TASTEER_WORDS = [
    "ابن العاهره", "يا ابن القحبه", "يا ابن الدعاره", "كس ام اهلك", "كسم امك", "يا ديوث", "يا جرار",
    "يا فحل اختك", "يا فحل امك", "انيك امك", "كسس اهلك", "مسوي تسوي قوي صح", "يا خنيث", "وش بك انيك أمك",
    "يا ابن الساقطه", "يا فحل خواتك", "شو بك كس امك", "مسوي تسوي غبي صح", "يا ديوث يا جرار",
    "يا ابن المتناكه", "يا شرمطه", "يا عاهر", "يا خول", "يا قواد", "يا منيوك", "يا ابن الحزانه",
    "يا وسخ", "يا جربان", "يا نجس", "يا رجس", "يا منفوح", "يا معفن", "يا خبيث", "يا رذيل",
    "يا حقير", "يا دنيء", "يا فاسق", "يا فاجر", "يا ملوث", "يا زب الكلب", "يا ابن الكلب",
    "يا ابن الحمار", "يا ابن البقره", "يا تيس", "يا حمار", "يا كلب", "يا خنزير", "يا قرد"
]

bot = AsyncTeleBot(BOT_TOKEN)

# =============== دوال Telethon ===============
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
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
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
    if not is_subscribed(user_id):
        await bot.send_message(chat_id, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
        return
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

# =============== أوامر البوت ===============
@bot.message_handler(commands=['start'])
async def start(message):
    user_id = message.from_user.id
    subscribed = is_subscribed(user_id)
    status = "✅ مفعل" if subscribed else "❌ غير مفعل"
    
    welcome_text = f"""
<b>🔥 بـوت فـشـار 🔥</b>

━━━━━━━━━━━━━━━━━━━━
<b>🤖 المبرمج:</b> <i>الداهية ايليا الملائكة</i>
<b>👑 الاونر:</b> <i>@Dwojj</i>
━━━━━━━━━━━━━━━━━━━━

<b>📊 حالة الاشتراك:</b> {status}

<b>⚡ الأوامر المتاحة:</b>
• /login - تسجيل الدخول بحسابك
• /takleesh - بدء التكليش
• /tasteer - بدء التسطير
• /stop - إيقاف العملية
• /subscribe - الاشتراك بالبوت
• /myplan - معرفة باقي اشتراكك

━━━━━━━━━━━━━━━━━━━━
<i>البوّاب اللي يفتح لك أبواب العيور</i>
"""
    await bot.reply_to(message, welcome_text, parse_mode="HTML")

@bot.message_handler(commands=['subscribe'])
async def subscribe(message):
    user_id = message.from_user.id
    text = f"""
<b>⭐ نظام الاشتراكات ⭐</b>

━━━━━━━━━━━━━━━━━━━━
<b>💎 عن طريق النجوم:</b>

⭐ 15 نجمة = ساعة واحدة
⭐ 50 نجمة = يوم واحد
⭐ 150 نجمة = أسبوع واحد
⭐ 250 نجمة = شهر كامل

━━━━━━━━━━━━━━━━━━━━
<i>أرسل النجوم مباشرة إلى البوت</i>
"""
    await bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['myplan'])
async def myplan(message):
    user_id = str(message.from_user.id)
    if user_id in subscriptions:
        expiry = subscriptions[user_id]
        remaining = datetime.fromisoformat(expiry) - datetime.now()
        hours = remaining.total_seconds() // 3600
        await bot.reply_to(message, f"✅ اشتراكك فعال لمدة {int(hours)} ساعة متبقية")
    else:
        await bot.reply_to(message, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")

# أمر خاص بالاونر فقط
@bot.message_handler(commands=['subscription'])
async def subscription_cmd(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        await bot.reply_to(message, "❌ هذا الأمر خاص بالأونر فقط")
        return
    
    args = message.text.split()
    if len(args) != 3:
        await bot.reply_to(message, "❌ الاستخدام:\n/subscription [ايدي المستخدم] [عدد الساعات]")
        return
    
    target_id = int(args[1])
    hours = int(args[2])
    
    add_subscription(target_id, hours)
    await bot.reply_to(message, f"✅ تم تفعيل اشتراك للمستخدم {target_id} لمدة {hours} ساعة")

@bot.message_handler(commands=['login'])
async def login(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
        return
    if is_verified(user_id):
        await bot.reply_to(message, "✅ أنت مسجل بالفعل")
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
        await bot.reply_to(message, f"❌ كود خطأ")
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
        await bot.reply_to(message, f"❌ كلمة مرور خطأ")
        del user_steps[user_id]

@bot.message_handler(commands=['takleesh'])
async def takleesh(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
        return
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
    if not is_subscribed(user_id):
        await bot.reply_to(message, "❌ ليس لديك اشتراك نشط\nاستخدم /subscribe للاشتراك")
        return
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

# معالجة الاشتراك بالنجوم
@bot.pre_checkout_query_handler(func=lambda query: True)
async def checkout(pre_checkout_query):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
async def successful_payment(message):
    user_id = message.from_user.id
    total_amount = message.successful_payment.total_amount // 100  # بالنجوم
    
    if total_amount == 15:
        add_subscription(user_id, 1)  # ساعة
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة ساعة واحدة")
    elif total_amount == 50:
        add_subscription(user_id, 24)  # يوم
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة يوم واحد")
    elif total_amount == 150:
        add_subscription(user_id, 168)  # أسبوع
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة أسبوع")
    elif total_amount == 250:
        add_subscription(user_id, 720)  # شهر
        await bot.reply_to(message, "✅ تم تفعيل اشتراكك لمدة شهر")
    else:
        await bot.reply_to(message, "❌ مبلغ غير صحيح")

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
