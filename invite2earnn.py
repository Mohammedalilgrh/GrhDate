from flask import Flask
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import asyncio
import os

# إعدادات البوت
API_ID = 21706160
API_HASH = '548b91f0e7cd2e44bbee05190620d9f4'
BOT_TOKEN = '7551982212:AAHSgM4JuGnOBBzafGqGFZhY1-gwVo7g4nY'
CHANNEL_USERNAME = "@invite2earnn"
ORDER_CHANNEL = "@invite2orders"

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return {"status": "Invite2Earn Bot is running!"}

# تشغيل البوت
bot = Client("invite2earnn", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# قاعدة البيانات
def init_db():
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        code TEXT,
        balance REAL,
        referrals INTEGER,
        left_referrals INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS referral_logs (
        referrer_id INTEGER,
        referred_id INTEGER,
        joined INTEGER DEFAULT 1
    )''')
    conn.commit()
    return conn, c

conn, c = init_db()

def generate_code(user_id):
    return f"C{user_id}D"

async def check_subscription(client, user_id):
    try:
        member = await client.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("شراء كود الربح الخاص بي", callback_data="buy_code")],
        [InlineKeyboardButton("ربّحني الآن $", callback_data="share_link")],
        [InlineKeyboardButton("اسحب أموالي الآن", callback_data="withdraw")]
    ])

@bot.on_message(filters.command("start"))
async def start(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "None"
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    subscribed = await check_subscription(client, user_id)
    if not subscribed:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("الاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("تم الاشتراك ✅", callback_data="check_sub")]
        ])
        await message.reply("لبدء استخدام البوت يجب عليك الاشتراك بالقناة", reply_markup=keyboard)
        return

    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", (user_id, username, "", 0.0, 0, 0))
        conn.commit()

        if referral_code:
            referrer_id = int(referral_code[1:-1])
            c.execute("SELECT * FROM users WHERE user_id = ?", (referrer_id,))
            if c.fetchone():
                c.execute("INSERT INTO referral_logs (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user_id))
                c.execute("UPDATE users SET balance = balance + 0.1, referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
                conn.commit()

    code = generate_code(user_id)
    c.execute("UPDATE users SET code = ? WHERE user_id = ?", (code, user_id))
    conn.commit()

    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = c.fetchone()[0]

    await message.reply(
        f"1. اسم المستخدم: @{username}\n2. المبلغ الإجمالي: {balance:.2f}$\n3. كود الربح الخاص بك: {code}",
        reply_markup=main_menu()
    )

@bot.on_callback_query(filters.regex("check_sub"))
async def recheck_subscription(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    subscribed = await check_subscription(client, user_id)
    if subscribed:
        await callback_query.message.delete()
        await start(client, callback_query.message)
    else:
        await callback_query.answer("يرجى الاشتراك أولاً.", show_alert=True)

@bot.on_callback_query(filters.regex("buy_code"))
async def buy_code(client, callback_query: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("أسيا سيل", callback_data="pay_asiacell")],
        [InlineKeyboardButton("زين العراق", callback_data="pay_zain")],
        [InlineKeyboardButton("رجوع", callback_data="back")]
    ])
    await callback_query.message.edit_text("اختر طريقة الدفع لشراء كود الربح الخاص بك مقابل 2$:", reply_markup=keyboard)

@bot.on_callback_query(filters.regex("pay_(asiacell|zain)"))
async def process_payment(client, callback_query: CallbackQuery):
    method = callback_query.data.split("_")[1]
    await callback_query.message.edit_text(f"ارسل الآن رصيد {method} بقيمة 2$، ثم أرسل رقم الهاتف المرسل منه.")

@bot.on_message(filters.private & filters.text)
async def handle_private_text(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "None"
    text = message.text.strip()

    c.execute("SELECT code FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if not result:
        await message.reply("يرجى بدء البوت باستخدام /start أولاً.")
        return

    code = result[0]
    if text == code:
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        balance = user[3]
        if balance < 2.0:
            await message.reply("يجب أن يكون لديك على الأقل 2$ للسحب.")
            return

        await message.reply(
            f"تفاصيل السحب:\nالكود: {user[2]}\nالرصيد: {balance:.2f}$\n"
            f"الإحالات: {user[4]}\nالإلغاء: {user[5]}\nسيتم التواصل معك قريباً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("زين العراق", callback_data="withdraw_zain")],
                [InlineKeyboardButton("أسيا سيل", callback_data="withdraw_asiacell")],
                [InlineKeyboardButton("ماستر كارد/كي كارد", callback_data="withdraw_card")],
                [InlineKeyboardButton("عملة رقمية", callback_data="withdraw_crypto")]
            ])
        )
        await client.send_message(
            ORDER_CHANNEL,
            f"طلب سحب جديد:\nالمستخدم: @{username}\nالرصيد: {balance:.2f}$\n"
            f"الكود: {code}\nيرجى مراجعة الطلب."
        )
    else:
        await client.send_message(
            ORDER_CHANNEL,
            f"طلب شراء كود:\nالمستخدم: @{username}\nالرقم: {text}\nالكود: {code}"
        )
        await message.reply("تم إرسال طلبك، سيتم التواصل معك بعد التحقق.")

@bot.on_callback_query(filters.regex("share_link"))
async def share_link(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    c.execute("SELECT code FROM users WHERE user_id = ?", (user_id,))
    code = c.fetchone()[0]
    await callback_query.message.edit_text(
        f"شارك هذا الرابط مع أصدقائك: \nhttps://t.me/{await client.get_me().username}?start={code}\n"
        "كل شخص يدخل من رابطك ويشترك بالقناة تكسب 0.1$",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="back")]])
    )

@bot.on_callback_query(filters.regex("withdraw"))
async def withdraw_request(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("اكتب كود الربح الخاص بك للتحقق:")

@bot.on_callback_query(filters.regex("back"))
async def go_back(client, callback_query: CallbackQuery):
    await start(client, callback_query.message)

# فحص الاشتراكات دورياً
async def check_left_users():
    while True:
        c.execute("SELECT user_id, username FROM users")
        users = c.fetchall()
        for user_id, username in users:
            is_member = await check_subscription(bot, user_id)
            if not is_member:
                c.execute("UPDATE users SET balance = balance - 0.1, left_referrals = left_referrals + 1 WHERE user_id = ?", (user_id,))
                await bot.send_message(ORDER_CHANNEL, f"المستخدم @{username} ألغى الاشتراك في القناة.")
                conn.commit()
        await asyncio.sleep(3600)  # تحقق كل ساعة

# تشغيل البوت
async def start_bot():
    await bot.start()
    print("Invite2Earn bot is running...")
    asyncio.create_task(check_left_users())
    await asyncio.Event().wait()

# بدء التشغيل
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))).start()
