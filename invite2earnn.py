from flask import Flask, request
from threading import Thread
import telebot
from telebot import types
import sqlite3
import time
import logging

# Initialize
app = Flask(__name__)
TOKEN = '7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g'
CHANNELS = ["@intearnn", "@s111sgrh"]  # قنوات الاشتراك الإجباري
ORDER_CHANNEL = "@intorders"
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"  # أضف أي دي الأدمن هنا
bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)

# Database setup
def init_db():
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        code TEXT,
        balance REAL DEFAULT 0.0,
        referrals INTEGER DEFAULT 0,
        investment_link TEXT,
        joined_date DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Referrals table
    c.execute('''CREATE TABLE IF NOT EXISTS referral_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        reward_claimed BOOLEAN DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Payments table
    c.execute('''CREATE TABLE IF NOT EXISTS payment_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        phone_number TEXT,
        amount REAL,
        payment_method TEXT,
        status TEXT DEFAULT 'pending',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Withdrawals table
    c.execute('''CREATE TABLE IF NOT EXISTS withdrawal_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        method TEXT,
        account_info TEXT,
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
        logging.error(f"خطأ في التحقق من الاشتراك: {e}")
        return False

def get_user_info(user_id):
    c.execute("SELECT username, full_name FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if result:
        username, full_name = result
        return f"@{username}" if username and username != "None" else full_name
    return "مستخدم غير معروف"

def get_user_balance(user_id):
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    return c.fetchone()[0]

def update_user_balance(user_id, amount):
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

# Keyboard Markups
def main_menu_markup():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("💳 شراء كود الربح", callback_data="buy_code"),
        types.InlineKeyboardButton("💰 اسحب أموالي", callback_data="withdraw")
    )
    markup.row(
        types.InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
        types.InlineKeyboardButton("📢 رابط الإحالة", callback_data="share_link")
    )
    return markup

def back_to_main_markup():
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    return markup

def payment_methods_markup():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("أسيا سيل", callback_data="pay_asiacell"),
        types.InlineKeyboardButton("زين العراق", callback_data="pay_zain")
    )
    markup.row(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    return markup

def withdraw_methods_markup():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("زين العراق", callback_data="withdraw_zain"),
        types.InlineKeyboardButton("أسيا سيل", callback_data="withdraw_asiacell")
    )
    markup.row(
        types.InlineKeyboardButton("ماستر كارد/كي كارد", callback_data="withdraw_card"),
        types.InlineKeyboardButton("عملة رقمية", callback_data="withdraw_crypto")
    )
    markup.row(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    return markup

# Handlers
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "None"
    full_name = message.from_user.first_name
    if message.from_user.last_name:
        full_name += " " + message.from_user.last_name
    
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    # Check subscription
    if not check_subscription(user_id):
        show_subscription_alert(message)
        return
    
    # Register/update user
    code = generate_code(user_id)
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, code) VALUES (?, ?, ?, ?)",
             (user_id, username, full_name, code))
    c.execute("UPDATE users SET username = ?, full_name = ?, code = ? WHERE user_id = ?",
             (username, full_name, code, user_id))
    
    # Handle referral
    if referral_code and referral_code.startswith("C") and referral_code.endswith("D"):
        try:
            referrer_id = int(referral_code[1:-1])
            if referrer_id != user_id:  # Prevent self-referral
                c.execute("INSERT INTO referral_logs (referrer_id, referred_id) VALUES (?, ?)",
                         (referrer_id, user_id))
                update_user_balance(referrer_id, 0.1)
                c.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
        except Exception as e:
            logging.error(f"خطأ في نظام الإحالة: {e}")
    
    conn.commit()
    show_main_menu(message, user_id)

def show_subscription_alert(message):
    markup = types.InlineKeyboardMarkup()
    for channel in CHANNELS:
        markup.add(types.InlineKeyboardButton(f"اشترك في {channel}", url=f"https://t.me/{channel.strip('@')}"))
    markup.add(types.InlineKeyboardButton("✅ تم الاشتراك", callback_data="check_sub"))
    bot.send_message(message.chat.id, "⚠️ للبدء، يجب الاشتراك في القنوات التالية:", reply_markup=markup)

def show_main_menu(message, user_id=None):
    user_id = user_id or message.from_user.id
    c.execute("SELECT balance, code, referrals FROM users WHERE user_id = ?", (user_id,))
    balance, code, referrals = c.fetchone()
    
    text = (f"مرحباً {get_user_info(user_id)} 👋\n\n"
           f"💰 رصيدك: {balance:.2f}$\n"
           f"🔑 كودك: {code}\n"
           f"👥 أحالتك: {referrals}")
    
    if isinstance(message, types.CallbackQuery):
        bot.edit_message_text(text, message.message.chat.id, message.message.message_id, reply_markup=main_menu_markup())
    else:
        bot.send_message(message.chat.id, text, reply_markup=main_menu_markup())

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_subscription_callback(call):
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call)
    else:
        bot.answer_callback_query(call.id, "❗ لم تكمل الاشتراك في جميع القنوات", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main_callback(call):
    show_main_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "buy_code")
def buy_code_callback(call):
    bot.edit_message_text(
        "💳 اختر طريقة الدفع لشراء كود الربح:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=payment_methods_markup()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def payment_method_callback(call):
    method = call.data.split("_")[1]
    method_name = "أسيا سيل" if method == "asiacell" else "زين العراق"
    
    msg = bot.edit_message_text(
        f"🔔 طريقة الدفع: {method_name}\n\n"
        "📌 أرسل رقم الرصيد الآن:\n"
        "(يجب أن يكون الرصيد 2$ على الأقل)",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back_to_main_markup()
    )
    bot.register_next_step_handler(msg, lambda m: process_payment(m, method))

def process_payment(message, method):
    user_id = message.from_user.id
    phone_number = message.text.strip()
    
    # Save payment request
    c.execute("INSERT INTO payment_requests (user_id, phone_number, amount, payment_method) VALUES (?, ?, ?, ?)",
             (user_id, phone_number, 2.0, method))
    
    # Prepare admin notification
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_{user_id}"),
        types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
    )
    
    admin_msg = (f"📌 طلب دفع جديد:\n\n"
                f"👤 المستخدم: {get_user_info(user_id)}\n"
                f"📱 الرقم: {phone_number}\n"
                f"💳 الطريقة: {'أسيا سيل' if method == 'asiacell' else 'زين العراق'}\n"
                f"🔑 الكود: {generate_code(user_id)}")
    
    bot.send_message(ORDER_CHANNEL, admin_msg, reply_markup=markup)
    bot.reply_to(message, "📬 تم استلام طلبك، جاري المراجعة...", reply_markup=back_to_main_markup())
    conn.commit()

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_admin_decision(call):
    action, user_id = call.data.split("_")
    user_id = int(user_id)
    
    if action == "approve":
        investment_link = f"https://t.me/{bot.get_me().username}?start=inv_{user_id}"
        c.execute("UPDATE users SET investment_link = ? WHERE user_id = ?", (investment_link, user_id))
        c.execute("UPDATE payment_requests SET status = 'approved' WHERE user_id = ? AND status = 'pending'", (user_id,))
        
        try:
            bot.send_message(
                user_id,
                f"🎉 تم تفعيل حسابك بنجاح!\n\n"
                f"🔗 رابط الإحالة الخاص بك:\n{investment_link}\n\n"
                f"📌 شارك الرابط مع الأصدقاء لربح المزيد",
                reply_markup=main_menu_markup()
            )
        except Exception as e:
            logging.error(f"فشل إرسال الرسالة: {e}")
        
        bot.answer_callback_query(call.id, "تم القبول")
    else:
        c.execute("UPDATE payment_requests SET status = 'rejected' WHERE user_id = ? AND status = 'pending'", (user_id,))
        try:
            bot.send_message(
                user_id,
                "❌ تم رفض طلبك، يرجى المحاولة لاحقاً",
                reply_markup=main_menu_markup()
            )
        except Exception as e:
            logging.error(f"فشل إرسال الرسالة: {e}")
        
        bot.answer_callback_query(call.id, "تم الرفض")
    
    conn.commit()
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "share_link")
def share_link_callback(call):
    user_id = call.from_user.id
    code = generate_code(user_id)
    link = f"https://t.me/{bot.get_me().username}?start={code}"
    
    text = (f"🔗 رابط الإحالة الخاص بك:\n{link}\n\n"
           f"📌 شارك هذا الرابط مع أصدقائك:\n"
           f"- 0.1$ لكل تسجيل جديد\n"
           f"- 0.5$ لكل عملية شراء\n"
           f"- أرباح غير محدودة!")
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back_to_main_markup()
    )

@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def withdraw_callback(call):
    user_id = call.from_user.id
    balance = get_user_balance(user_id)
    
    if balance < 2.0:
        bot.answer_callback_query(call.id, "❗ الحد الأدنى للسحب 2$", show_alert=True)
        return
    
    msg = bot.edit_message_text(
        "📤 لسحب الأموال:\n\n"
        "أرسل كود الربح الخاص بك للتأكيد:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back_to_main_markup()
    )
    bot.register_next_step_handler(msg, verify_withdraw_code)

def verify_withdraw_code(message):
    user_id = message.from_user.id
    user_code = generate_code(user_id)
    
    if message.text.strip() == user_code:
        bot.reply_to(
            message,
            "💰 اختر طريقة السحب:",
            reply_markup=withdraw_methods_markup()
        )
    else:
        bot.reply_to(
            message,
            "❌ الكود غير صحيح",
            reply_markup=back_to_main_markup()
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_"))
def withdraw_method_callback(call):
    method = call.data.split("_")[1]
    method_names = {
        "zain": "زين العراق",
        "asiacell": "أسيا سيل",
        "card": "ماستر كارد/كي كارد",
        "crypto": "عملة رقمية"
    }
    
    msg = bot.edit_message_text(
        f"📤 أرسل معلومات {method_names[method]} للسحب:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back_to_main_markup()
    )
    bot.register_next_step_handler(msg, lambda m: process_withdraw(m, method))

def process_withdraw(message, method):
    user_id = message.from_user.id
    account_info = message.text.strip()
    balance = get_user_balance(user_id)
    
    # Save withdrawal request
    c.execute("INSERT INTO withdrawal_requests (user_id, amount, method, account_info) VALUES (?, ?, ?, ?)",
             (user_id, balance, method, account_info))
    
    # Deduct balance
    update_user_balance(user_id, -balance)
    
    # Notify admin
    admin_msg = (f"📤 طلب سحب جديد:\n\n"
                f"👤 المستخدم: {get_user_info(user_id)}\n"
                f"💵 المبلغ: {balance:.2f}$\n"
                f"💳 الطريقة: {method}\n"
                f"📝 المعلومات: {account_info}")
    
    bot.send_message(ORDER_CHANNEL, admin_msg)
    bot.reply_to(
        message,
        f"✅ تم استلام طلب السحب\n"
        f"⏳ جاري المعالجة خلال 24 ساعة",
        reply_markup=main_menu_markup()
    )
    conn.commit()

@bot.callback_query_handler(func=lambda call: call.data == "my_stats")
def stats_callback(call):
    user_id = call.from_user.id
    c.execute("SELECT balance, referrals, joined_date FROM users WHERE user_id = ?", (user_id,))
    balance, referrals, join_date = c.fetchone()
    
    c.execute("SELECT COUNT(*) FROM referral_logs WHERE referrer_id = ?", (user_id,))
    total_refs = c.fetchone()[0]
    
    text = (f"📊 إحصائياتك:\n\n"
           f"💰 الرصيد: {balance:.2f}$\n"
           f"👥 أحالتك: {referrals}\n"
           f"📅 تاريخ الانضمام: {join_date[:10]}\n"
           f"🔗 إجمالي الإحالات: {total_refs}")
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back_to_main_markup()
    )

# Flask routes
@app.route('/' + TOKEN, methods=['POST'])
def bot_webhook():
    json_data = request.get_data().decode('utf-8')
    update = types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "OK", 200

@app.route('/')
def set_webhook():
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url='https://invite2earnn.onrender.com + TOKEN)
    return "Webhook is set!", 200

if __name__ == '__main__':
    print("Bot is running...")
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url='https://invite2earnn.onrender.com + TOKEN)
    app.run(host="0.0.0.0", port=5000)
