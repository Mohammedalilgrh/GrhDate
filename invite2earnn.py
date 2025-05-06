from flask import Flask, request
from threading import Thread
import telebot
from telebot import types
import sqlite3
import time

app = Flask(__name__)
TOKEN = '7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g'
CHANNELS = ["@intearnn", "@s111sgrh"]  # Mandatory channels
ORDER_CHANNEL = "@intorders"
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"
bot = telebot.TeleBot(TOKEN)

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
        left_referrals INTEGER DEFAULT 0,
        investment_link TEXT,
        last_menu TEXT
    )''')
    
    # Referrals table
    c.execute('''CREATE TABLE IF NOT EXISTS referral_logs (
        referrer_id INTEGER,
        referred_id INTEGER,
        joined INTEGER DEFAULT 1,
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
        print(f"Subscription check error: {e}")
        return False

def get_user_display(user_id):
    c.execute("SELECT username, full_name FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if user:
        username, full_name = user
        if username and username != "None":
            return f"@{username}"
        return full_name or "مستخدم غير معروف"
    return "مستخدم غير معروف"

def update_last_menu(user_id, menu_name):
    c.execute("UPDATE users SET last_menu = ? WHERE user_id = ?", (menu_name, user_id))
    conn.commit()

def get_last_menu(user_id):
    c.execute("SELECT last_menu FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else None

# Menu functions
def main_menu(user_id=None):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("💰 شراء كود الربح", callback_data="buy_code"),
        types.InlineKeyboardButton("💸 ربحني الآن", callback_data="share_link")
    )
    markup.row(types.InlineKeyboardButton("💳 سحب الرصيد", callback_data="withdraw"))
    
    if user_id:
        update_last_menu(user_id, "main_menu")
    return markup

def back_button(menu_name):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"back_{menu_name}"))
    return markup

# Bot handlers
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "None"
    full_name = message.from_user.first_name or ""
    if message.from_user.last_name:
        full_name += f" {message.from_user.last_name}"
    
    args = message.text.split()
    referral_code = args[1] if len(args) > 1 else None

    # Check channel subscription
    if not check_subscription(user_id):
        keyboard = types.InlineKeyboardMarkup()
        for channel in CHANNELS:
            keyboard.add(types.InlineKeyboardButton(f"اشترك في {channel}", url=f"https://t.me/{channel.strip('@')}"))
        keyboard.add(types.InlineKeyboardButton("✅ تم الاشتراك", callback_data="check_sub"))
        
        bot.reply_to(message, 
                    "📢 للبدء يجب الاشتراك في القنوات التالية:",
                    reply_markup=keyboard)
        return

    # Register/update user
    c.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, username, full_name, code) VALUES (?, ?, ?, ?)", 
                 (user_id, username, full_name, ""))
        conn.commit()
        
        if referral_code and referral_code.startswith("C") and referral_code.endswith("D"):
            try:
                referrer_id = int(referral_code[1:-1])
                c.execute("SELECT 1 FROM users WHERE user_id = ?", (referrer_id,))
                if c.fetchone():
                    c.execute("INSERT INTO referral_logs (referrer_id, referred_id) VALUES (?, ?)", 
                             (referrer_id, user_id))
                    c.execute("UPDATE users SET balance = balance + 0.1, referrals = referrals + 1 WHERE user_id = ?", 
                             (referrer_id,))
                    conn.commit()
            except:
                pass

    # Generate/update user code
    user_code = generate_code(user_id)
    c.execute("UPDATE users SET code = ?, username = ?, full_name = ? WHERE user_id = ?", 
              (user_code, username, full_name, user_id))
    conn.commit()

    # Get user balance
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = c.fetchone()[0]

    # Display main menu
    user_display = get_user_display(user_id)
    bot.reply_to(message,
                f"👋 أهلاً بك {user_display}\n\n"
                f"💼 رصيدك الحالي: {balance:.2f}$\n"
                f"🆔 كودك الخاص: {user_code}\n"
                f"👥 أحالتك: {c.execute('SELECT COUNT(*) FROM referral_logs WHERE referrer_id = ?', (user_id,)).fetchone()[0]}",
                reply_markup=main_menu(user_id))

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_subscription_handler(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start_command(call.message)
    else:
        bot.answer_callback_query(call.id, "❗ يجب الاشتراك في جميع القنوات أولاً", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "buy_code")
def buy_code_menu(call):
    user_id = call.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🔵 أسيا سيل", callback_data="pay_asiacell"),
        types.InlineKeyboardButton("🟢 زين العراق", callback_data="pay_zain")
    )
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main_menu"))
    
    update_last_menu(user_id, "buy_code")
    bot.edit_message_text(
        "💳 اختر طريقة الدفع لشراء كود الاستثمار:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def payment_method_handler(call):
    method = call.data.split("_")[1]
    user_id = call.from_user.id
    
    update_last_menu(user_id, f"pay_{method}")
    msg = bot.edit_message_text(
        f"📥 لشراء كود الاستثمار:\n\n"
        f"1. أرسل رقم رصيد {'أسيا سيل' if method == 'asiacell' else 'زين العراق'} الفعال\n"
        f"2. سيتم التحقق تلقائياً\n"
        f"3. بعد التأكيد يصلك كودك\n\n"
        f"🔢 الرجاء إرسال رقم الرصيد الآن:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back_button("buy_code")
    )
    bot.register_next_step_handler(msg, lambda m: process_payment(m, method))

def process_payment(message, method):
    user_id = message.from_user.id
    phone = message.text.strip()
    
    if not phone.isdigit() or len(phone) < 10:
        bot.reply_to(message, "❌ رقم غير صحيح، يرجى إرسال رقم صحيح", reply_markup=back_button("buy_code"))
        return
    
    # Save payment request
    c.execute("INSERT INTO payment_requests (user_id, phone_number, amount, payment_method) VALUES (?, ?, ?, ?)",
              (user_id, phone, 2.0, method))
    conn.commit()
    
    # Get user info
    user_info = get_user_display(user_id)
    user_code = generate_code(user_id)
    
    # Send to admin channel
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_{user_id}"),
        types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
    )
    
    bot.send_message(
        ORDER_CHANNEL,
        f"🛒 طلب شراء كود جديد:\n\n"
        f"👤 المستخدم: {user_info}\n"
        f"📞 الرقم: {phone}\n"
        f"💳 الطريقة: {'أسيا سيل' if method == 'asiacell' else 'زين العراق'}\n"
        f"🆔 الكود: {user_code}",
        reply_markup=markup
    )
    
    # Confirm to user
    bot.reply_to(
        message,
        f"📩 تم استلام طلبك:\n\n"
        f"📱 الرقم: {phone}\n"
        f"💳 الطريقة: {'أسيا سيل' if method == 'asiacell' else 'زين العراق'}\n\n"
        f"⏳ جاري التحقق...",
        reply_markup=back_button("main_menu")
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def payment_decision_handler(call):
    action, user_id = call.data.split("_")
    user_id = int(user_id)
    
    if action == "approve":
        # Generate unique link
        invite_link = f"https://t.me/{bot.get_me().username}?start=inv_{user_id}"
        
        # Update database
        c.execute("UPDATE users SET investment_link = ? WHERE user_id = ?", (invite_link, user_id))
        c.execute("UPDATE payment_requests SET status = 'approved' WHERE user_id = ? AND status = 'pending'", (user_id,))
        conn.commit()
        
        # Notify admin
        bot.send_message(
            ORDER_CHANNEL,
            f"✅ تم تفعيل كود للمستخدم {get_user_display(user_id)}\n"
            f"🔗 الرابط: {invite_link}"
        )
        
        # Send to user
        try:
            bot.send_message(
                user_id,
                f"🎉 تم تفعيل كودك بنجاح!\n\n"
                f"🔐 كودك: {generate_code(user_id)}\n"
                f"🔗 رابط الإحالة:\n{invite_link}\n\n"
                f"📤 شارك الرابط لتحصل على عمولة",
                reply_markup=main_menu(user_id)
            )
        except Exception as e:
            print(f"Failed to send message: {e}")
        
        bot.answer_callback_query(call.id, "تم القبول")
    else:
        # Update database
        c.execute("UPDATE payment_requests SET status = 'rejected' WHERE user_id = ? AND status = 'pending'", (user_id,))
        conn.commit()
        
        # Notify admin
        bot.send_message(
            ORDER_CHANNEL,
            f"❌ تم رفض طلب {get_user_display(user_id)}"
        )
        
        # Send to user
        try:
            bot.send_message(
                user_id,
                "⚠️ تم رفض طلبك، يرجى:\n\n"
                "1. التأكد من صحة الرصيد\n"
                "2. التأكد من كفاية المبلغ\n"
                "3. المحاولة مرة أخرى",
                reply_markup=main_menu(user_id)
            )
        except Exception as e:
            print(f"Failed to send message: {e}")
        
        bot.answer_callback_query(call.id, "تم الرفض")

@bot.callback_query_handler(func=lambda call: call.data == "share_link")
def share_link_handler(call):
    user_id = call.from_user.id
    user_code = generate_code(user_id)
    
    update_last_menu(user_id, "share_link")
    bot.edit_message_text(
        f"🔗 رابط الإحالة الخاص بك:\n"
        f"https://t.me/{bot.get_me().username}?start={user_code}\n\n"
        f"📤 شارك الرابط لتحصل على:\n"
        f"- 0.1$ لكل اشتراك\n"
        f"- 0.5$ لكل عملية شراء\n"
        f"- أرباح متزايدة",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back_button("main_menu")
    )

@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def withdraw_handler(call):
    user_id = call.from_user.id
    
    update_last_menu(user_id, "withdraw")
    msg = bot.edit_message_text(
        "💸 لسحب أموالك:\n\n"
        "1. تأكد أن رصيدك 2$ كحد أدنى\n"
        "2. أكتب كودك للتحقق\n\n"
        "🔢 الرجاء إرسال الكود الآن:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back_button("main_menu")
    )
    bot.register_next_step_handler(msg, verify_withdraw_code)

def verify_withdraw_code(message):
    user_id = message.from_user.id
    input_code = message.text.strip()
    user_code = generate_code(user_id)
    
    if input_code != user_code:
        bot.reply_to(message, "❌ الكود غير صحيح", reply_markup=back_button("main_menu"))
        return
    
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = c.fetchone()[0]
    
    if balance < 2.0:
        bot.reply_to(message, "⚠️ الرصيد غير كافي (2$ حد أدنى)", reply_markup=main_menu(user_id))
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🔵 أسيا سيل", callback_data="withdraw_asiacell"),
        types.InlineKeyboardButton("🟢 زين العراق", callback_data="withdraw_zain")
    )
    markup.row(
        types.InlineKeyboardButton("💳 كي كارد", callback_data="withdraw_card"),
        types.InlineKeyboardButton("💰 كريبتو", callback_data="withdraw_crypto")
    )
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main_menu"))
    
    update_last_menu(user_id, "withdraw_method")
    bot.reply_to(
        message,
        f"💵 رصيدك: {balance:.2f}$\n\n"
        f"اختر طريقة السحب:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_"))
def withdraw_method_handler(call):
    method = call.data.split("_")[1]
    user_id = call.from_user.id
    
    method_names = {
        "asiacell": "أسيا سيل",
        "zain": "زين العراق",
        "card": "ماستر/كي كارد",
        "crypto": "عملة رقمية"
    }
    
    update_last_menu(user_id, f"withdraw_{method}")
    msg = bot.edit_message_text(
        f"📤 لسحب الأموال عبر {method_names[method]}:\n\n"
        f"1. تأكد من صحة المعلومات\n"
        f"2. أرسل رقم {method_names[method]} للاستلام\n\n"
        f"🔢 الرجاء إرسال المعلومات الآن:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=back_button("withdraw")
    )
    bot.register_next_step_handler(msg, lambda m: process_withdraw(m, method))

def process_withdraw(message, method):
    user_id = message.from_user.id
    account_info = message.text.strip()
    
    c.execute("SELECT balance, code FROM users WHERE user_id = ?", (user_id,))
    balance, user_code = c.fetchone()
    
    method_names = {
        "asiacell": "أسيا سيل",
        "zain": "زين العراق",
        "card": "ماستر/كي كارد",
        "crypto": "عملة رقمية"
    }
    
    # Send to admin
    bot.send_message(
        ORDER_CHANNEL,
        f"📤 طلب سحب جديد:\n\n"
        f"👤 المستخدم: {get_user_display(user_id)}\n"
        f"💵 المبلغ: {balance:.2f}$\n"
        f"🆔 الكود: {user_code}\n"
        f"💳 الطريقة: {method_names[method]}\n"
        f"📝 المعلومات: {account_info}"
    )
    
    # Confirm to user
    bot.reply_to(
        message,
        f"📬 تم استلام طلبك:\n\n"
        f"💵 المبلغ: {balance:.2f}$\n"
        f"💳 الطريقة: {method_names[method]}\n\n"
        f"⏳ سيتم التحويل خلال 24 ساعة",
        reply_markup=main_menu(user_id)
    )

# Back button handler
@bot.callback_query_handler(func=lambda call: call.data.startswith("back_"))
def back_handler(call):
    user_id = call.from_user.id
    target_menu = call.data.split("_")[1]
    
    if target_menu == "main_menu":
        start_command(call.message)
    elif target_menu == "buy_code":
        buy_code_menu(call)
    elif target_menu == "withdraw":
        withdraw_handler(call)
    else:
        last_menu = get_last_menu(user_id)
        if last_menu == "buy_code":
            buy_code_menu(call)
        elif last_menu == "withdraw":
            withdraw_handler(call)
        else:
            start_command(call.message)

# Flask routes
@app.route('/' + TOKEN, methods=['POST'])
def webhook_handler():
    json_update = request.stream.read().decode('utf-8')
    update = types.Update.de_json(json_update)
    bot.process_new_updates([update])
    return '!', 200

@app.route('/')
def set_webhook():
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g')
    return 'Webhook set!', 200

if __name__ == '__main__':
    print("🤖 Bot is running...")
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g')
    app.run(host="0.0.0.0", port=5000)
