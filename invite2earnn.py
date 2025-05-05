import os
import asyncio
import sqlite3
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Configuration (hardcoded for your setup)
BOT_TOKEN = '7897542906:AAGn878y8jEqD3eG55kIHpTNoe8lKnTOKco'  # Replace with your actual bot token
CHANNEL_USERNAME = "@intearnn"
ORDER_CHANNEL = "@intorders"

# Initialize Flask app
app = Flask(__name__)

@app.route("/")
def home():
    return {"status": "Bot is running!"}

# Initialize Pyrogram client with minimal configuration
bot = Client(
    "my_bot",
    bot_token=BOT_TOKEN,
    in_memory=True,
    no_updates=True  # Disable unnecessary update handling
)

# Database setup
def init_db():
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        username TEXT, 
        code TEXT,
        balance REAL DEFAULT 0.0, 
        referrals INTEGER DEFAULT 0, 
        left_referrals INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS referral_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER, 
        referred_id INTEGER UNIQUE, 
        joined INTEGER DEFAULT 1,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    return conn, c

conn, c = init_db()

# Helper functions
def generate_code(user_id):
    return f"C{user_id}D"

async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
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

# Bot command handlers
@bot.on_message(filters.command("start"))
async def start_command(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "None"
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    if not await check_subscription(user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("الاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("تم الاشتراك ✅", callback_data="check_sub")]
        ])
        await message.reply("لبدء استخدام البوت يجب عليك الاشتراك بالقناة", reply_markup=keyboard)
        return

    c.execute("INSERT OR IGNORE INTO users (user_id, username, code) VALUES (?, ?, ?)", 
             (user_id, username, ""))
    
    if referral_code:
        try:
            referrer_id = int(referral_code[1:-1])
            if referrer_id != user_id:
                c.execute("INSERT OR IGNORE INTO referral_logs (referrer_id, referred_id) VALUES (?, ?)", 
                         (referrer_id, user_id))
                c.execute("UPDATE users SET balance = balance + 0.1, referrals = referrals + 1 WHERE user_id = ?", 
                         (referrer_id,))
        except Exception as e:
            print(f"Referral processing error: {e}")

    code = generate_code(user_id)
    c.execute("UPDATE users SET code = ? WHERE user_id = ?", (code, user_id))
    conn.commit()

    balance = c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]

    await message.reply(
        f"1. اسم المستخدم: @{username}\n"
        f"2. المبلغ الإجمالي: {balance:.2f}$\n"
        f"3. كود الربح الخاص بك: {code}",
        reply_markup=main_menu()
    )

@bot.on_callback_query(filters.regex("check_sub"))
async def check_sub_callback(client, callback_query: CallbackQuery):
    if await check_subscription(callback_query.from_user.id):
        await callback_query.message.delete()
        await start_command(client, callback_query.message)
    else:
        await callback_query.answer("لم يتم الاشتراك بعد!", show_alert=True)

@bot.on_callback_query(filters.regex("buy_code"))
async def buy_code_handler(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "لشراء الكود، يرجى إرسال 2$ إلى أحد الأرقام التالية:\n"
        "1. زين كاش: 07701234567\n"
        "2. آسيا سيل: 07501234567\n"
        "ثم أرسل إيصال الدفع",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("رجوع", callback_data="back")]
        ])
    )

@bot.on_callback_query(filters.regex("share_link"))
async def share_link_handler(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    code = c.execute("SELECT code FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
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
async def withdraw_handler(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("اكتب كود الربح الخاص بك للتحقق:")

@bot.on_callback_query(filters.regex("back"))
async def back_handler(client, callback_query: CallbackQuery):
    await start_command(client, callback_query.message)

@bot.on_message(filters.private & filters.text & ~filters.command("start"))
async def handle_text_messages(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "None"
    text = message.text.strip()

    code = c.execute("SELECT code FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
    
    if text == code:
        balance = c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
        
        if balance < 2.0:
            await message.reply("يجب أن يكون لديك على الأقل 2$ للسحب.")
            return

        await message.reply(
            f"تفاصيل السحب:\n"
            f"الكود: {code}\n"
            f"الرصيد: {balance:.2f}$\n\n"
            f"سيتم التواصل معك قريباً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("زين العراق", callback_data="withdraw_zain")],
                [InlineKeyboardButton("أسيا سيل", callback_data="withdraw_asiacell")]
            ])
        )
        
        await client.send_message(
            ORDER_CHANNEL,
            f"طلب سحب جديد:\nالمستخدم: @{username}\nالرصيد: {balance:.2f}$\nالكود: {code}"
        )
    else:
        await client.send_message(
            ORDER_CHANNEL,
            f"طلب شراء كود:\nالمستخدم: @{username}\nالرقم: {text}\nالكود: {code}"
        )
        await message.reply("تم إرسال طلبك، سيتم التواصل معك بعد التحقق.")

# Subscription monitoring
async def monitor_subscriptions():
    while True:
        try:
            users = c.execute("SELECT user_id, username FROM users").fetchall()
            for user_id, username in users:
                if not await check_subscription(user_id):
                    c.execute("UPDATE users SET balance = balance - 0.1, left_referrals = left_referrals + 1 WHERE user_id = ?", (user_id,))
                    await bot.send_message(
                        ORDER_CHANNEL, 
                        f"المستخدم @{username} ألغى الاشتراك في القناة."
                    )
            conn.commit()
        except Exception as e:
            print(f"Monitoring error: {e}")
        await asyncio.sleep(3600)

# Flask runner
def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

# Bot runner
async def run_bot():
    await bot.start()
    print("Bot started successfully!")
    asyncio.create_task(monitor_subscriptions())
    await asyncio.Event().wait()

if __name__ == "__main__":
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("Bot stopped")
    finally:
        conn.close()
