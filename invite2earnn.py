import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
from flask import Flask
import threading

# Flask app for web server
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Telegram Bot is Running!", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=5000)

# إعدادات البوت
API_ID = 21706160
API_HASH = "548b91f0e7cd2e44bbee05190620d9f4"
BOT_TOKEN = "7551982212:AAHSgM4JuGnOBBzafGqGFZhY1-gwVo7g4nY"
CHANNEL_USERNAME = "@invite2earnn"  # تأكد من أن البوت مشرف في القناة
ORDER_CHANNEL = "@invite2orders"

# Initialize Pyrogram client
app = Client("invite2earnn", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# قاعدة البيانات
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (user_id INTEGER PRIMARY KEY, 
              username TEXT, 
              code TEXT, 
              balance REAL, 
              referrals INTEGER, 
              left_referrals INTEGER)''')
conn.commit()

# توليد كود فريد
def generate_code(user_id):
    return f"C{user_id}D"

# نظام التحقق من الاشتراك (مُحسّن)
async def check_subscription(user_id):
    try:
        member = await app.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except UserNotParticipant:
        return False
    except ChatAdminRequired:
        print(f"⚠️ البوت ليس مشرفاً في القناة {CHANNEL_USERNAME}")
        return False
    except Exception as e:
        print(f"❌ خطأ في التحقق من الاشتراك: {e}")
        return False

# واجهة الاشتراك
def subscription_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 انضم للقناة", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("✅ تأكيد الاشتراك", callback_data="verify_sub")]
    ])

# القائمة الرئيسية
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 شراء كود الربح", callback_data="buy_code")],
        [InlineKeyboardButton("💰 ربحني الآن", callback_data="share_link")],
        [InlineKeyboardButton("💸 سحب الأرباح", callback_data="withdraw")]
    ])

# بدء البوت
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    user = message.from_user
    user_id = user.id
    username = user.username or "None"
    
    # التحقق من الاشتراك
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        await message.reply(
            f"🔒 للوصول إلى البوت، يرجى الاشتراك في قناتنا:\n{CHANNEL_USERNAME}\n\n"
            "بعد الاشتراك اضغط على زر التأكيد",
            reply_markup=subscription_keyboard(),
            disable_web_page_preview=True
        )
        return
    
    # إدارة بيانات المستخدم
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_data = c.fetchone()
    
    if not user_data:
        user_code = generate_code(user_id)
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", 
                 (user_id, username, user_code, 0.0, 0, 0))
        conn.commit()
    else:
        user_code = user_data[2]
    
    # جلب رصيد المستخدم
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = c.fetchone()[0]
    
    await message.reply(
        f"👤 معلومات حسابك:\n\n"
        f"🆔 المعرف: @{username}\n"
        f"💰 الرصيد: ${balance:.2f}\n"
        f"🔑 كودك: {user_code}\n\n"
        "اختر أحد الخيارات:",
        reply_markup=main_menu()
    )

# تأكيد الاشتراك
@app.on_callback_query(filters.regex("^verify_sub$"))
async def verify_subscription(client, callback_query: CallbackQuery):
    user = callback_query.from_user
    try:
        is_subscribed = await check_subscription(user.id)
        
        if is_subscribed:
            await callback_query.message.delete()
            await start(client, callback_query.message)
        else:
            await callback_query.answer(
                "❌ لم نجد اشتراكك. يرجى الانضمام للقناة أولاً ثم الضغط على الزر مرة أخرى.",
                show_alert=True
            )
    except Exception as e:
        print(f"خطأ في تأكيد الاشتراك: {e}")
        await callback_query.answer(
            "حدث خطأ أثناء التحقق. يرجى المحاولة لاحقاً.",
            show_alert=True
        )

# شراء كود الربح
@app.on_callback_query(filters.regex("^buy_code$"))
async def buy_code(client, callback_query: CallbackQuery):
    await callback_query.answer("🚀 سيتم توجيهك لشراء الكود قريباً...", show_alert=True)
    await callback_query.message.reply(
        "🛒 لشراء كود الربح:\n\n"
        "1. ستحصل على كود خاص بك\n"
        "2. يمكنك مشاركته مع الآخرين\n"
        "3. تربح من كل شخص يستخدم كودك\n\n"
        "سيتم تفعيل هذه الخدمة قريباً",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ])
    )

# مشاركة الرابط
@app.on_callback_query(filters.regex("^share_link$"))
async def share_link(client, callback_query: CallbackQuery):
    user = callback_query.from_user
    user_code = generate_code(user.id)
    share_text = (
        f"🚀 انضم إلى برنامج الربح من التوصيات!\n\n"
        f"🔗 رابطك الخاص: https://t.me/{(await app.get_me()).username}?start={user_code}\n\n"
        f"📌 لكل شخص يسجل عبر رابطك، ستحصل على مكافأة!"
    )
    await callback_query.message.reply(
        share_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 مشاركة الرابط", url=f"https://t.me/share/url?url={share_text}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ])
    )

# سحب الأرباح
@app.on_callback_query(filters.regex("^withdraw$"))
async def withdraw(client, callback_query: CallbackQuery):
    user = callback_query.from_user
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user.id,))
    balance = c.fetchone()[0]
    
    if balance < 10:  # حد السحب الأدنى
        await callback_query.answer(
            f"❌ الرصيد غير كافي للسحب. الحد الأدنى للسحب هو $10. رصيدك الحالي: ${balance:.2f}",
            show_alert=True
        )
    else:
        await callback_query.message.reply(
            f"💰 رصيدك الحالي: ${balance:.2f}\n\n"
            "يرجى إرسال تفاصيل محفظتك (PayPal أو غيرها) لاستكمال عملية السحب.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="back_to_main")]
            ])
        )

# العودة للقائمة الرئيسية
@app.on_callback_query(filters.regex("^back_to_main$"))
async def back_to_main(client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    await start(client, callback_query.message)

def run_telegram_bot():
    print("✅ البوت يعمل بنجاح...")
    app.run()

if __name__ == "__main__":
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start Telegram bot
    run_telegram_bot()
