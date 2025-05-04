import os
import asyncio
import sqlite3
from threading import Thread
from flask import Flask, request
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Bot settings
API_ID = 21706160
API_HASH = '548b91f0e7cd2e44bbee05190620d9f4'
BOT_TOKEN = '7551982212:AAHSgM4JuGnOBBzafGqGFZhY1-gwVo7g4nY'
CHANNEL_USERNAME = "@invite2earnn"
ORDER_CHANNEL = "@invite2orders"

# Flask App
app = Flask(__name__)

@app.route("/")
def home():
    return {"status": "Invite2Earn Bot is running!"}

# Initialize the bot
bot = Client("invite2earnn", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database setup
def init_db():
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        username TEXT, 
        code TEXT,
        balance REAL, 
        referrals INTEGER, 
        left_referrals INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referral_logs (
        referrer_id INTEGER, 
        referred_id INTEGER, 
        joined INTEGER DEFAULT 1)''')
    conn.commit()
    return conn, c

conn, c = init_db()

# Helper functions
def generate_code(user_id):
    return f"C{user_id}D"

async def check_subscription(client, user_id):
    try:
        member = await client.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        print(f"Subscription check error: {e}")
        return False

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("شراء كود الربح الخاص بي", callback_data="buy_code")],
        [InlineKeyboardButton("ربّحني الآن $", callback_data="share_link")],
        [InlineKeyboardButton("اسحب أموالي الآن", callback_data="withdraw")]
    ])

# Bot commands and handlers
@bot.on_message(filters.command("start"))
async def start_command(client, message: Message):
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
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", 
                 (user_id, username, "", 0.0, 0, 0))
        conn.commit()
        if referral_code:
            try:
                referrer_id = int(referral_code[1:-1])
                c.execute("SELECT * FROM users WHERE user_id = ?", (referrer_id,))
                if c.fetchone():
                    c.execute("INSERT INTO referral_logs (referrer_id, referred_id) VALUES (?, ?)", 
                             (referrer_id, user_id))
                    c.execute("UPDATE users SET balance = balance + 0.1, referrals = referrals + 1 WHERE user_id = ?", 
                             (referrer_id,))
                    conn.commit()
            except Exception as e:
                print(f"Referral error: {e}")

    code = generate_code(user_id)
    c.execute("UPDATE users SET code = ? WHERE user_id = ?", (code, user_id))
    conn.commit()

    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = c.fetchone()[0]

    await message.reply(
        f"1. اسم المستخدم: @{username}\n"
        f"2. المبلغ الإجمالي: {balance:.2f}$\n"
        f"3. كود الربح الخاص بك: {code}",
        reply_markup=main_menu()
    )

@bot.on_callback_query(filters.regex("check_sub"))
async def check_sub_again(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if await check_subscription(client, user_id):
        await callback_query.message.delete()
        await start_command(client, callback_query.message)
    else:
        await callback_query.answer("يرجى الاشتراك أولاً.", show_alert=True)

@bot.on_callback_query(filters.regex("buy_code"))
async def buy_code_menu(client, callback_query: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("أسيا سيل", callback_data="pay_asiacell")],
        [InlineKeyboardButton("زين العراق", callback_data="pay_zain")],
        [InlineKeyboardButton("رجوع", callback_data="back")]
    ])
    await callback_query.message.edit_text(
        "اختر طريقة الدفع لشراء كود الربح الخاص بك مقابل 2$:", 
        reply_markup=keyboard
    )

@bot.on_callback_query(filters.regex("pay_(asiacell|zain)"))
async def pay_now(client, callback_query: CallbackQuery):
    method = callback_query.data.split("_")[1]
    await callback_query.message.edit_text(
        f"ارسل الآن رصيد {method} بقيمة 2$، ثم أرسل رقم الهاتف المرسل منه."
    )

@bot.on_callback_query(filters.regex("share_link"))
async def show_share_link(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    c.execute("SELECT code FROM users WHERE user_id = ?", (user_id,))
    code = c.fetchone()[0]
    bot_username = (await client.get_me()).username
    await callback_query.message.edit_text(
        f"شارك هذا الرابط مع أصدقائك:\n"
        f"https://t.me/{bot_username}?start={code}\n\n"
        f"كل شخص يدخل من رابطك ويشترك بالقناة تكسب 0.1$",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("رجوع", callback_data="back")]
        ])
    )

@bot.on_callback_query(filters.regex("withdraw"))
async def request_withdraw(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("اكتب كود الربح الخاص بك للتحقق:")

@bot.on_callback_query(filters.regex("back"))
async def back_to_menu(client, callback_query: CallbackQuery):
    await start_command(client, callback_query.message)

@bot.on_message(filters.private & filters.text & ~filters.command("start"))
async def handle_text_message(client, message: Message):
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
            f"تفاصيل السحب:\n"
            f"الكود: {user[2]}\n"
            f"الرصيد: {balance:.2f}$\n"
            f"الإحالات: {user[4]}\n"
            f"الإلغاء: {user[5]}\n\n"
            f"سيتم التواصل معك قريباً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("زين العراق", callback_data="withdraw_zain")],
                [InlineKeyboardButton("أسيا سيل", callback_data="withdraw_asiacell")],
                [InlineKeyboardButton("ماستر كارد/كي كارد", callback_data="withdraw_card")],
                [InlineKeyboardButton("عملة رقمية", callback_data="withdraw_crypto")]
            ])
        )
        await client.send_message(
            ORDER_CHANNEL,
            f"طلب سحب جديد:\nالمستخدم: @{username}\nالرصيد: {balance:.2f}$\nالكود: {code}\nيرجى مراجعة الطلب."
        )
    else:
        await client.send_message(
            ORDER_CHANNEL,
            f"طلب شراء كود:\nالمستخدم: @{username}\nالرقم: {text}\nالكود: {code}"
        )
        await message.reply("تم إرسال طلبك، سيتم التواصل معك بعد التحقق.")

# Subscription monitoring
async def monitor_unsubscribes():
    while True:
        try:
            c.execute("SELECT user_id, username FROM users")
            users = c.fetchall()
            for user_id, username in users:
                if not await check_subscription(bot, user_id):
                    c.execute("UPDATE users SET balance = balance - 0.1, left_referrals = left_referrals + 1 WHERE user_id = ?", (user_id,))
                    await bot.send_message(
                        ORDER_CHANNEL, 
                        f"المستخدم @{username} ألغى الاشتراك في القناة."
                    )
            conn.commit()
        except Exception as e:
            print(f"Monitoring error: {e}")
        await asyncio.sleep(3600)  # Check every hour

# Run the bot
async def run_bot():
    await bot.start()
    print("Bot started!")
    asyncio.create_task(monitor_unsubscribes())
    await asyncio.Event().wait()

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Run the bot in the main thread
    asyncio.run(run_bot())
