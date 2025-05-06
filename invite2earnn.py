from flask import Flask, request
from threading import Thread
import telebot
from telebot import types
import sqlite3
import time

app = Flask(__name__)
TOKEN = '7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g'
CHANNELS = ["@intearnn", "@s111sgrh"]  # قنوات الاشتراك الإجباري
ORDER_CHANNEL = "@intorders"
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"  # أضف أي دي الأدمن هنا
bot = telebot.TeleBot(TOKEN)

# Database setup
def init_db():
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        code TEXT,
        balance REAL,
        referrals INTEGER,
        left_referrals INTEGER,
        investment_link TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS referral_logs (
        referrer_id INTEGER,
        referred_id INTEGER,
        joined INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS payment_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        phone_number TEXT,
        amount REAL,
        payment_method TEXT,
        status TEXT DEFAULT 'pending',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    return conn, c

conn, c = init_db()

# Helper functions
def generate_code(user_id):
    return f"C{user_id}D"

def check_subscription(user_id):
    try:
        for channel in CHANNELS:
            chat_member = bot.get_chat_member(channel, user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                return False
        return True
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False

def get_user_info(user_id):
    c.execute("SELECT username, full_name FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if result:
        username, full_name = result
        if username and username != "None":
            return f"@{username}"
        elif full_name:
            return full_name
    return "مستخدم غير معروف"

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
    full_name = message.from_user.first_name
    if message.from_user.last_name:
        full_name += " " + message.from_user.last_name
    
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    # Check channel subscription
    subscribed = check_subscription(user_id)
    if not subscribed:
        keyboard = types.InlineKeyboardMarkup()
        for channel in CHANNELS:
            keyboard.row(types.InlineKeyboardButton(f"الاشتراك في {channel}", url=f"https://t.me/{channel.strip('@')}"))
        keyboard.row(types.InlineKeyboardButton("تم الاشتراك ✅", callback_data="check_sub"))
        bot.reply_to(message, "لبدء استخدام البوت يجب عليك الاشتراك في القنوات التالية:", reply_markup=keyboard)
        return

    # Register new user or update existing
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()

    if not user:
        c.execute("INSERT INTO users (user_id, username, full_name, code, balance, referrals, left_referrals) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                 (user_id, username, full_name, "", 0.0, 0, 0))
        conn.commit()
        if referral_code:
            referrer_id = int(referral_code[1:-1])
            c.execute("SELECT * FROM users WHERE user_id = ?", (referrer_id,))
            if c.fetchone():
                c.execute("INSERT INTO referral_logs (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user_id))
                c.execute("UPDATE users SET balance = balance + 0.1, referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
                conn.commit()

    # Generate or update user code
    code = generate_code(user_id)
    c.execute("UPDATE users SET code = ?, username = ?, full_name = ? WHERE user_id = ?", 
              (code, username, full_name, user_id))
    conn.commit()

    # Get user balance
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = c.fetchone()[0]

    # Display user info
    user_display_name = get_user_info(user_id)
    bot.reply_to(
        message,
        f"مرحباً {user_display_name}\n\n"
        f"1. المبلغ الإجمالي: {balance:.2f}$\n"
        f"2. كود الربح الخاص بك: {code}\n"
        f"3. عدد الإحالات: {c.execute('SELECT COUNT(*) FROM referral_logs WHERE referrer_id = ?', (user_id,)).fetchone()[0]}",
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_again(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start_command(call.message)
    else:
        bot.answer_callback_query(call.id, "يرجى الاشتراك في جميع القنوات أولاً.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "buy_code")
def buy_code_menu(call):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("أسيا سيل", callback_data="pay_asiacell"),
        types.InlineKeyboardButton("زين العراق", callback_data="pay_zain")
    )
    keyboard.row(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    bot.edit_message_text(
        "اختر طريقة الدفع لشراء كود الاستثمار الخاص بك:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def request_payment_info(call):
    method = call.data.split("_")[1]
    method_name = "أسيا سيل" if method == "asiacell" else "زين العراق"
    
    msg = bot.edit_message_text(
        f"📌 لشراء كود الاستثمار الخاص بك:\n\n"
        f"1. أرسل رقم رصيد {method_name} الفعال\n"
        f"2. سوف يتم التحقق من الرصيد تلقائياً\n"
        f"3. بعد التأكيد سيصلك كود الاستثمار الخاص بك\n\n"
        f"♦️ الرجاء إرسال رقم الرصيد الآن:",
        call.message.chat.id,
        call.message.message_id
    )
    bot.register_next_step_handler(msg, lambda m: process_payment(m, method))

def process_payment(message, method):
    user_id = message.from_user.id
    phone_number = message.text.strip()
    
    # Save payment request to database
    c.execute("INSERT INTO payment_requests (user_id, phone_number, amount, payment_method) VALUES (?, ?, ?, ?)",
              (user_id, phone_number, 2.0, method))
    conn.commit()
    
    # Get user info
    user_info = get_user_info(user_id)
    c.execute("SELECT code FROM users WHERE user_id = ?", (user_id,))
    user_code = c.fetchone()[0]
    
    # Send to order channel with approve/reject buttons
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_{user_id}"),
        types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
    )
    
    bot.send_message(
        ORDER_CHANNEL,
        f"📌 طلب شراء كود استثمار جديد:\n\n"
        f"👤 المستخدم: {user_info}\n"
        f"📱 الرقم: {phone_number}\n"
        f"💳 الطريقة: {'أسيا سيل' if method == 'asiacell' else 'زين العراق'}\n"
        f"🆔 كود المستخدم: {user_code}",
        reply_markup=keyboard
    )
    
    # Send confirmation to user
    bot.reply_to(
        message,
        f"📬 تم استلام طلبك بنجاح!\n\n"
        f"♦️ رقم الرصيد: {phone_number}\n"
        f"💳 طريقة الدفع: {'أسيا سيل' if method == 'asiacell' else 'زين العراق'}\n\n"
        f"جاري التحقق من الرصيد...\n"
        f"سيصلك إشعار عند التأكيد."
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_payment_decision(call):
    action, user_id = call.data.split("_")
    user_id = int(user_id)
    
    if action == "approve":
        # Generate investment link
        investment_link = f"https://t.me/{bot.get_me().username}?start=inv_{user_id}"
        
        # Update user in database
        c.execute("UPDATE users SET investment_link = ? WHERE user_id = ?", (investment_link, user_id))
        c.execute("UPDATE payment_requests SET status = 'approved' WHERE user_id = ? AND status = 'pending'", (user_id,))
        conn.commit()
        
        # Send to admin channel
        bot.send_message(
            ORDER_CHANNEL,
            f"✅ تم قبول طلب المستخدم {get_user_info(user_id)}\n"
            f"🔗 رابط الإحالة: {investment_link}"
        )
        
        # Send to user
        try:
            bot.send_message(
                user_id,
                f"🎉 تهانينا! تم تفعيل كود الاستثمار الخاص بك\n\n"
                f"🔐 كودك: {generate_code(user_id)}\n"
                f"🔗 رابط الإحالة الخاص بك:\n{investment_link}\n\n"
                f"📌 شارك هذا الرابط مع أصدقائك لتحصل على عمولة."
            )
        except Exception as e:
            print(f"Error sending message to user: {e}")
        
        bot.answer_callback_query(call.id, "تم القبول وإرسال الرابط للمستخدم")
    else:
        c.execute("UPDATE payment_requests SET status = 'rejected' WHERE user_id = ? AND status = 'pending'", (user_id,))
        conn.commit()
        
        # Send to admin channel
        bot.send_message(
            ORDER_CHANNEL,
            f"❌ تم رفض طلب المستخدم {get_user_info(user_id)}"
        )
        
        # Send to user
        try:
            bot.send_message(
                user_id,
                "⚠️ تم رفض طلبك، يرجى التأكد من:\n\n"
                "1. أن الرصيد المرسل صحيح\n"
                "2. أن الرصيد كافي (2$)\n"
                "3. إعادة المحاولة أو التواصل مع الدعم"
            )
        except Exception as e:
            print(f"Error sending message to user: {e}")
        
        bot.answer_callback_query(call.id, "تم الرفض وإعلام المستخدم")

@bot.callback_query_handler(func=lambda call: call.data == "share_link")
def show_share_link(call):
    user_id = call.from_user.id
    c.execute("SELECT code FROM users WHERE user_id = ?", (user_id,))
    code = c.fetchone()[0]
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    
    bot.edit_message_text(
        f"🔗 رابط الإحالة الخاص بك:\n"
        f"https://t.me/{bot.get_me().username}?start={code}\n\n"
        f"📌 شارك هذا الرابط مع أصدقائك:\n"
        f"- كل شخص يسجل عبر رابطك يكسبك 0.1$\n"
        f"- عندما يكملون عملية الشراء تكسب 0.5$\n"
        f"- أرباحك تزيد مع كل شخص يدخل عبرك",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def request_withdraw(call):
    bot.edit_message_text(
        "📤 لسحب أموالك:\n\n"
        "1. تأكد أن لديك رصيد 2$ كحد أدنى\n"
        "2. اكتب كود الربح الخاص بك للتحقق\n\n"
        "♦️ الرجاء إرسال الكود الآن:",
        call.message.chat.id,
        call.message.message_id
    )
    bot.register_next_step_handler(call.message, process_withdraw_request)

def process_withdraw_request(message):
    user_id = message.from_user.id
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
        balance = user[4]  # balance is at index 4
        
        if balance < 2.0:
            bot.reply_to(message, "⚠️ يجب أن يكون لديك على الأقل 2$ للسحب.")
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
        keyboard.row(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))

        bot.reply_to(
            message,
            f"💰 تفاصيل السحب:\n\n"
            f"🆔 كودك: {user[3]}\n"
            f"💵 الرصيد المتاح: {balance:.2f}$\n"
            f"👥 عدد الإحالات: {user[5]}\n\n"
            f"📤 اختر طريقة السحب:",
            reply_markup=keyboard
        )
    else:
        bot.reply_to(message, "⚠️ الكود غير صحيح، يرجى المحاولة مرة أخرى.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_"))
def handle_withdraw_method(call):
    method = call.data.split("_")[1]
    user_id = call.from_user.id
    
    method_name = {
        "zain": "زين العراق",
        "asiacell": "أسيا سيل",
        "card": "ماستر كارد/كي كارد",
        "crypto": "عملة رقمية"
    }.get(method, method)
    
    msg = bot.edit_message_text(
        f"📤 لاستلام أموالك عبر {method_name}:\n\n"
        f"1. تأكد من صحة المعلومات\n"
        f"2. أرسل رقم {method_name} الذي تريد الاستلام عليه\n\n"
        f"♦️ الرجاء إرسال المعلومات الآن:",
        call.message.chat.id,
        call.message.message_id
    )
    bot.register_next_step_handler(msg, lambda m: finalize_withdraw(m, method, user_id))

def finalize_withdraw(message, method, user_id):
    account_info = message.text.strip()
    
    # Get user balance
    c.execute("SELECT balance, code FROM users WHERE user_id = ?", (user_id,))
    balance, user_code = c.fetchone()
    
    method_name = {
        "zain": "زين العراق",
        "asiacell": "أسيا سيل",
        "card": "ماستر كارد/كي كارد",
        "crypto": "عملة رقمية"
    }.get(method, method)
    
    # Send to order channel
    bot.send_message(
        ORDER_CHANNEL,
        f"📤 طلب سحب جديد:\n\n"
        f"👤 المستخدم: {get_user_info(user_id)}\n"
        f"💵 المبلغ: {balance:.2f}$\n"
        f"🆔 الكود: {user_code}\n"
        f"💳 الطريقة: {method_name}\n"
        f"📝 معلومات الحساب: {account_info}"
    )
    
    bot.reply_to(
        message,
        f"📬 تم استلام طلب السحب بنجاح!\n\n"
        f"💵 المبلغ: {balance:.2f}$\n"
        f"💳 الطريقة: {method_name}\n\n"
        f"سيتم التواصل معك خلال 24 ساعة لإتمام العملية."
    )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main_menu(call):
    start_command(call.message)

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
    bot.set_webhook(url='https://invite2earnn.onrender.com/' + TOKEN)
    return 'Webhook set!', 200

if __name__ == '__main__':
    print("Bot is running...")
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url='https://invite2earnn.onrender.com/' + TOKEN)
    app.run(host="0.0.0.0", port=5000)
