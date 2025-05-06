from flask import Flask, request
from threading import Thread
import telebot
from telebot import types
import sqlite3
import time

app = Flask(__name__)
TOKEN = '7897542906:AAGn878y8jEqD3eG55kIHpTNoe8lKnTOKco'
CHANNEL_USERNAME = "@intearnn"
ORDER_CHANNEL = "@intorders"
bot = telebot.TeleBot(TOKEN)

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

# Helper functions
def generate_code(user_id):
    return f"C{user_id}D"

def check_subscription(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except:
        return False

def main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("شراء كود الربح الخاص بي", callback_data="buy_code"),
        types.InlineKeyboardButton("ربّحني الآن $", callback_data="share_link")
    )
    markup.row(types.InlineKeyboardButton("اسحب أموالي الآن", callback_data="withdraw"))
    return markup

# Bot handlers
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "None"
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    subscribed = check_subscription(user_id)
    if not subscribed:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("الاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")
        )
        keyboard.row(types.InlineKeyboardButton("تم الاشتراك ✅", callback_data="check_sub"))
        bot.reply_to(message, "لبدء استخدام البوت يجب عليك الاشتراك بالقناة", reply_markup=keyboard)
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

    bot.reply_to(
        message,
        f"1. اسم المستخدم: @{username}\n"
        f"2. المبلغ الإجمالي: {balance:.2f}$\n"
        f"3. كود الربح الخاص بك: {code}",
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_again(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start_command(call.message)
    else:
        bot.answer_callback_query(call.id, "يرجى الاشتراك أولاً.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "buy_code")
def buy_code_menu(call):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("أسيا سيل", callback_data="pay_asiacell"),
        types.InlineKeyboardButton("زين العراق", callback_data="pay_zain")
    )
    keyboard.row(types.InlineKeyboardButton("رجوع", callback_data="back"))
    bot.edit_message_text(
        "اختر طريقة الدفع لشراء كود الربح الخاص بك مقابل 2$:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def pay_now(call):
    method = call.data.split("_")[1]
    bot.edit_message_text(
        f"ارسل الآن رصيد {method} بقيمة 2$، ثم أرسل رقم الهاتف المرسل منه.",
        call.message.chat.id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == "share_link")
def show_share_link(call):
    user_id = call.from_user.id
    c.execute("SELECT code FROM users WHERE user_id = ?", (user_id,))
    code = c.fetchone()[0]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("رجوع", callback_data="back"))
    bot.edit_message_text(
        f"شارك هذا الرابط مع أصدقائك:\n"
        f"https://t.me/{bot.get_me().username}?start={code}\n\n"
        f"كل شخص يدخل من رابطك ويشترك بالقناة تكسب 0.1$",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def request_withdraw(call):
    bot.edit_message_text(
        "اكتب كود الربح الخاص بك للتحقق:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == "back")
def back_to_menu(call):
    start_command(call.message)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_message(message):
    user_id = message.from_user.id
    username = message.from_user.username or "None"
    text = message.text.strip()

    c.execute("SELECT code FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if not result:
        bot.reply_to(message, "يرجى بدء البوت باستخدام /start أولاً.")
        return

    code = result[0]
    if text == code:
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        balance = user[3]
        if balance < 2.0:
            bot.reply_to(message, "يجب أن يكون لديك على الأقل 2$ للسحب.")
            return

        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("زين العراق", callback_data="withdraw_zain"),
            types.InlineKeyboardButton("أسيا سيل", callback_data="withdraw_asiacell")
        )
        keyboard.row(
            types.InlineKeyboardButton("ماستر كارد/كي كارد", callback_data="withdraw_card"),
            types.InlineKeyboardButton("عملة رقمية", callback_data="withdraw_crypto")
        )

        bot.reply_to(
            message,
            f"تفاصيل السحب:\n"
            f"الكود: {user[2]}\n"
            f"الرصيد: {balance:.2f}$\n"
            f"الإحالات: {user[4]}\n"
            f"الإلغاء: {user[5]}\n\n"
            f"سيتم التواصل معك قريباً.",
            reply_markup=keyboard
        )

        bot.send_message(
            ORDER_CHANNEL,
            f"طلب سحب جديد:\nالمستخدم: @{username}\nالرصيد: {balance:.2f}$\nالكود: {code}\nيرجى مراجعة الطلب."
        )
    else:
        bot.send_message(
            ORDER_CHANNEL,
            f"طلب شراء كود:\nالمستخدم: @{username}\nالرقم: {text}\nالكود: {code}"
        )
        bot.reply_to(message, "تم إرسال طلبك، سيتم التواصل معك بعد التحقق.")

# Flask routes
@app.route('/' + TOKEN, methods=['POST'])
def get_message():
    json_update = request.stream.read().decode('utf-8')
    update = types.Update.de_json(json_update)
    bot.process_new_updates([update])
    return '!', 200

@app.route('/')
def webhook():
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url='https://invite2earnn.onrender.com/TOKEN')
    return 'Webhook set!', 200

if __name__ == '__main__':
    print("Bot is running...")
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url='https://invite2earnn.onrender.com/+TOKEN')
    app.run(host="0.0.0.0", port=5000)
