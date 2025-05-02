import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant, ChatAdminRequired

# إعدادات البوت
API_ID = 21706160
API_HASH = "548b91f0e7cd2e44bbee05190620d9f4"
BOT_TOKEN = "7551982212:AAHSgM4JuGnOBBzafGqGFZhY1-gwVo7g4nY"
CHANNEL_USERNAME = "@invite2earnn"
ORDER_CHANNEL = "@invite2orders"

# إنشاء تطبيق البوت
app = Client(
    "invite2earn_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# إعداد قاعدة البيانات
def setup_database():
    conn = sqlite3.connect("bot_database.db", check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        code TEXT UNIQUE,
        balance REAL DEFAULT 0.0,
        referrals INTEGER DEFAULT 0,
        left_referrals INTEGER DEFAULT 0,
        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    return conn, cursor

db_conn, db_cursor = setup_database()

# توليد كود مستخدم فريد
def generate_user_code(user_id):
    return f"INVITE-{user_id}-CODE"

# التحقق من الاشتراك في القناة (مُحسّن)
async def verify_channel_subscription(user_id):
    try:
        chat_member = await app.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except UserNotParticipant:
        return False
    except ChatAdminRequired:
        print(f"البوت ليس مشرفًا في القناة {CHANNEL_USERNAME}")
        return True  # تجاهل الخطأ إذا كان البوت ليس مشرفًا
    except Exception as e:
        print(f"خطأ في التحقق من الاشتراك: {e}")
        return False

# لوحة المفاتيح الرئيسية
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 شراء كود الربح", callback_data="buy_code")],
        [InlineKeyboardButton("💰 ربحني الآن", callback_data="earn_money")],
        [InlineKeyboardButton("💸 سحب الأرباح", callback_data="withdraw")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")]
    ])

# معالجة أمر /start
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    user = message.from_user
    referral_code = None
    
    # التحقق من وجود كود إحالة
    if len(message.command) > 1:
        referral_code = message.command[1]
    
    # التحقق من الاشتراك في القناة
    is_subscribed = await verify_channel_subscription(user.id)
    
    if not is_subscribed:
        join_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("انضم للقناة", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("✅ تأكيد الاشتراك", callback_data="check_sub")]
        ])
        await message.reply_text(
            f"👋 مرحبًا {user.first_name}!\n\n"
            "🔒 للوصول إلى جميع ميزات البوت، يرجى الاشتراك في قناتنا:\n"
            f"{CHANNEL_USERNAME}\n\n"
            "بعد الاشتراك اضغط على زر التأكيد",
            reply_markup=join_keyboard
        )
        return
    
    # تسجيل المستخدم الجديد
    db_cursor.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
    user_data = db_cursor.fetchone()
    
    if not user_data:
        user_code = generate_user_code(user.id)
        db_cursor.execute(
            "INSERT INTO users (user_id, username, code) VALUES (?, ?, ?)",
            (user.id, user.username, user_code)
        )
        
        # معالجة الإحالة إذا وجدت
        if referral_code:
            db_cursor.execute(
                "UPDATE users SET balance = balance + 0.5, referrals = referrals + 1 "
                "WHERE code = ?", (referral_code,)
            db_cursor.execute(
                "UPDATE users SET balance = balance + 0.5 "
                "WHERE user_id = ?", (user.id,))
        
        db_conn.commit()
    else:
        user_code = user_data[2]
    
    # عرض معلومات المستخدم
    db_cursor.execute(
        "SELECT balance, referrals FROM users WHERE user_id = ?", 
        (user.id,))
    balance, referrals = db_cursor.fetchone()
    
    await message.reply_text(
        f"🎉 أهلاً بك في بوت Invite2Earn!\n\n"
        f"👤 معرفك: @{user.username}\n"
        f"🆔 كودك الخاص: {user_code}\n"
        f"💰 رصيدك: ${balance:.2f}\n"
        f"👥 عدد الإحالات: {referrals}\n\n"
        "اختر أحد الخيارات من الأسفل:",
        reply_markup=get_main_keyboard()
    )

# زر تأكيد الاشتراك
@app.on_callback_query(filters.regex("^check_sub$"))
async def check_subscription_callback(client, callback_query: CallbackQuery):
    user = callback_query.from_user
    
    try:
        is_subscribed = await verify_channel_subscription(user.id)
        
        if is_subscribed:
            await callback_query.message.delete()
            await start_command(client, callback_query.message)
        else:
            await callback_query.answer(
                "⚠️ لم يتم العثور على اشتراكك. يرجى الانضمام للقناة أولاً!",
                show_alert=True
            )
    except Exception as e:
        print(f"Error in subscription check: {e}")
        await callback_query.answer(
            "❌ حدث خطأ أثناء التحقق. يرجى المحاولة لاحقاً.",
            show_alert=True
        )

# معالجة شراء الكود
@app.on_callback_query(filters.regex("^buy_code$"))
async def buy_code_handler(client, callback_query: CallbackQuery):
    payment_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 باي بال", callback_data="pay_paypal")],
        [InlineKeyboardButton("📱 تحويل مصرفي", callback_data="pay_bank")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
    ])
    
    await callback_query.message.edit_text(
        "💳 طرق الدفع المتاحة:\n\n"
        "1. باي بال - 2$\n"
        "2. تحويل بنكي - 2$\n\n"
        "اختر طريقة الدفع المناسبة:",
        reply_markup=payment_keyboard
    )

# معالجة ربح المال
@app.on_callback_query(filters.regex("^earn_money$"))
async def earn_money_handler(client, callback_query: CallbackQuery):
    user = callback_query.from_user
    
    db_cursor.execute("SELECT code FROM users WHERE user_id = ?", (user.id,))
    user_code = db_cursor.fetchone()[0]
    
    invite_link = f"https://t.me/{(await app.get_me()).username}?start={user_code}"
    
    await callback_query.message.edit_text(
        f"📣 رابط الدعوة الخاص بك:\n\n{invite_link}\n\n"
        "🎁 لكل شخص يسجل باستخدام رابطك:\n"
        "- تحصل على 0.5$\n"
        "- هو يحصل على 0.5$\n\n"
        "🔗 شارك الرابط مع أصدقائك واكسب المال!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
        ])
    )

# معالجة سحب الأرباح
@app.on_callback_query(filters.regex("^withdraw$"))
async def withdraw_handler(client, callback_query: CallbackQuery):
    user = callback_query.from_user
    
    db_cursor.execute(
        "SELECT balance FROM users WHERE user_id = ?", 
        (user.id,))
    balance = db_cursor.fetchone()[0]
    
    if balance < 5.0:
        await callback_query.answer(
            f"🚫 الحد الأدنى للسحب هو 5$. رصيدك الحالي: ${balance:.2f}",
            show_alert=True
        )
        return
    
    withdraw_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 باي بال", callback_data="withdraw_paypal")],
        [InlineKeyboardButton("📱 حوالة بنكية", callback_data="withdraw_bank")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
    ])
    
    await callback_query.message.edit_text(
        f"💵 رصيدك الحالي: ${balance:.2f}\n\n"
        "اختر طريقة السحب المفضلة:",
        reply_markup=withdraw_keyboard
    )

# معالجة العودة للقائمة الرئيسية
@app.on_callback_query(filters.regex("^main_menu$"))
async def back_to_main(client, callback_query: CallbackQuery):
    await start_command(client, callback_query.message)

# تشغيل البوت
if __name__ == "__main__":
    print("✅ البوت يعمل بنجاح...")
    app.run()
