from flask import Flask, request
from threading import Thread
import telebot
from telebot import types
import sqlite3
import time
import logging
from datetime import datetime

# Initialize app
app = Flask(__name__)
TOKEN = '7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g'
CHANNELS = ["@intearnn", "@s111sgrh"]  # Required channels
ORDER_CHANNEL = "@intorders"
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"
bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)

# Language texts
TEXTS = {
    'en': {
        'start': "Welcome {name} 👋\n\n💰 Current balance: {balance:.2f}$\n👥 Referrals: {refs}\n\n📌 Choose from menu:",
        'not_subscribed': "⚠️ To start, please join our channels:",
        'subscription_done': "✅ Done",
        'subscription_alert': "❗ You haven't joined all channels",
        'main_menu': ["💳 Buy Referral Code", "💰 Withdraw Earnings", "📊 My Stats", "🔄 Refresh Data"],
        'back_menu': "🔙 Main Menu",
        'payment_methods': ["💳 AsiaCell", "💳 Zain Iraq"],
        'withdraw_methods': ["💳 Zain Iraq", "💳 AsiaCell", "💳 MasterCard/KNet", "💳 Crypto"],
        'already_purchased': "✅ You already have an active referral code\n\n🔗 You can share this link:\n{link}\n\n💰 You'll earn 0.1$ per new referral",
        'purchase_info': "💳 To buy your referral code:\n\nCode price: 2$\nGives you the right to:\n- Earn 0.1$ per new referral\n- Share your unique link to earn more\n\nChoose payment method:",
        'enter_phone': "🔔 Payment method: {method}\n\n📌 Please send your phone number:\n(Must have at least 2$ balance)",
        'invalid_phone': "❌ Invalid number, please try again",
        'payment_request_sent': "📬 Your request received, under review...",
        'payment_approved': "🎉 Your referral code activated!\n\n🔗 Referral link:\n{link}\n\n💰 Earn 0.1$ for each signup via your link\n\n📌 Share this link to start earning",
        'payment_rejected': "❌ Your request was rejected, please check info and try later",
        'min_withdraw': "❗ Minimum withdrawal is 2$\n\nYou can increase your balance by:\n- Getting more referrals\n- Buying additional referral codes",
        'verify_code': "📤 To withdraw earnings:\n\nPlease send your referral code for verification:",
        'invalid_code': "❌ Verification code incorrect",
        'choose_withdraw': "💰 Choose withdrawal method:",
        'enter_withdraw_details': "📤 Please send your {method} details:",
        'withdraw_request_sent': "✅ Withdrawal request received\n\n⏳ Processing within 24 hours\n📌 You'll be notified when completed",
        'stats': "📊 Your stats:\n\n💰 Current balance: {balance:.2f}$\n👥 Active referrals: {refs}\n🔗 Total referrals: {total_refs}\n📅 Join date: {join_date}\n🔑 Referral code: {status}",
        'refresh_success': "✅ Data refreshed successfully",
        'error': "❌ Error occurred, please try later"
    },
    'ar': {
        'start': "أهلاً بك {name} 👋\n\n💰 رصيدك الحالي: {balance:.2f}$\n👥 عدد الإحالات: {refs}\n\n📌 اختر من القائمة:",
        'not_subscribed': "⚠️ للبدء، يرجى الانضمام إلى قنواتنا:",
        'subscription_done': "✅ تم",
        'subscription_alert': "❗ لم تنضم لجميع القنوات",
        'main_menu': ["💳 شراء كود إحالة", "💰 سحب الأرباح", "📊 إحصائياتي", "🔄 تحديث البيانات"],
        'back_menu': "🔙 القائمة الرئيسية",
        'payment_methods': ["💳 آسيا سيل", "💳 زين العراق"],
        'withdraw_methods': ["💳 زين العراق", "💳 آسيا سيل", "💳 ماستركارد/كي نت", "💳 كريبتو"],
        'already_purchased': "✅ لديك بالفعل كود إحالة نشط\n\n🔗 يمكنك مشاركة هذا الرابط:\n{link}\n\n💰 ستربح 0.1$ لكل إحالة جديدة",
        'purchase_info': "💳 لشراء كود الإحالة:\n\nسعر الكود: 2$\nيمنحك الحق في:\n- ربح 0.1$ لكل إحالة جديدة\n- مشاركة رابطك الخاص لربح المزيد\n\nاختر طريقة الدفع:",
        'enter_phone': "🔔 طريقة الدفع: {method}\n\n📌 يرجى إرسال رقم هاتفك:\n(يجب أن يحتوي على رصيد 2$ على الأقل)",
        'invalid_phone': "❌ رقم غير صحيح، يرجى المحاولة مرة أخرى",
        'payment_request_sent': "📬 تم استلام طلبك، قيد المراجعة...",
        'payment_approved': "🎉 تم تفعيل كود الإحالة الخاص بك!\n\n🔗 رابط الإحالة:\n{link}\n\n💰 اربح 0.1$ لكل اشتراك عبر رابطك\n\n📌 شارك هذا الرابط لبدء الربح",
        'payment_rejected': "❌ تم رفض طلبك، يرجى التحقق من المعلومات والمحاولة لاحقاً",
        'min_withdraw': "❗ الحد الأدنى للسحب هو 2$\n\nيمكنك زيادة رصيدك عن طريق:\n- الحصول على المزيد من الإحالات\n- شراء رموز إحالة إضافية",
        'verify_code': "📤 لسحب الأرباح:\n\nيرجى إرسال كود الإحالة الخاص بك للتحقق:",
        'invalid_code': "❌ كود التحقق غير صحيح",
        'choose_withdraw': "💰 اختر طريقة السحب:",
        'enter_withdraw_details': "📤 يرجى إرسال تفاصيل {method}:",
        'withdraw_request_sent': "✅ تم استلام طلب السحب\n\n⏳ جاري المعالجة خلال 24 ساعة\n📌 سيتم إعلامك عند الانتهاء",
        'stats': "📊 إحصائياتك:\n\n💰 الرصيد الحالي: {balance:.2f}$\n👥 الإحالات النشطة: {refs}\n🔗 إجمالي الإحالات: {total_refs}\n📅 تاريخ الانضمام: {join_date}\n🔑 كود الإحالة: {status}",
        'refresh_success': "✅ تم تحديث البيانات بنجاح",
        'error': "❌ حدث خطأ، يرجى المحاولة لاحقاً"
    }
}

# Enhanced database setup
def init_db():
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    
    # Users table with improvements
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        code TEXT UNIQUE,
        balance REAL DEFAULT 0.0,
        referrals INTEGER DEFAULT 0,
        has_purchased BOOLEAN DEFAULT 0,
        joined_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
        language TEXT DEFAULT 'en'
    )''')
    
    # Referrals tracking table
    c.execute('''CREATE TABLE IF NOT EXISTS referral_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER UNIQUE,
        reward_claimed BOOLEAN DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(referrer_id) REFERENCES users(user_id),
        FOREIGN KEY(referred_id) REFERENCES users(user_id)
    )''')
    
    # Payments tracking table
    c.execute('''CREATE TABLE IF NOT EXISTS payment_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        phone_number TEXT,
        amount REAL,
        payment_method TEXT,
        status TEXT DEFAULT 'pending',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')
    
    # Withdrawals tracking table
    c.execute('''CREATE TABLE IF NOT EXISTS withdrawal_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        method TEXT,
        account_info TEXT,
        status TEXT DEFAULT 'pending',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')
    
    conn.commit()
    return conn, c

conn, c = init_db()

# Helper functions
def get_user_language(user_id):
    c.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else 'en'

def get_text(key, user_id, **kwargs):
    lang = get_user_language(user_id)
    text = TEXTS[lang].get(key, TEXTS['en'].get(key, key))
    return text.format(**kwargs)

def generate_code(user_id):
    return f"PAID_{user_id}_{int(time.time())}"

def check_subscription(user_id):
    try:
        for channel in CHANNELS:
            chat_member = bot.get_chat_member(channel, user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                return False
        return True
    except Exception as e:
        logging.error(f"Subscription check error: {e}")
        return False

def get_user_info(user_id):
    c.execute("SELECT username, full_name FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if result:
        username, full_name = result
        return f"@{username}" if username and username != "None" else full_name
    return "Unknown User"

def update_user_activity(user_id):
    c.execute("UPDATE users SET last_active = ? WHERE user_id = ?", 
             (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

def get_user_balance(user_id):
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else 0.0

# Keyboard Markups
def main_menu_markup(user_id):
    lang = get_user_language(user_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row(TEXTS[lang]['main_menu'][0], TEXTS[lang]['main_menu'][1])
    markup.row(TEXTS[lang]['main_menu'][2], TEXTS[lang]['main_menu'][3])
    return markup

def payment_methods_markup(user_id):
    lang = get_user_language(user_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row(TEXTS[lang]['payment_methods'][0], TEXTS[lang]['payment_methods'][1])
    markup.row(TEXTS[lang]['back_menu'])
    return markup

def withdraw_methods_markup(user_id):
    lang = get_user_language(user_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row(TEXTS[lang]['withdraw_methods'][0], TEXTS[lang]['withdraw_methods'][1])
    markup.row(TEXTS[lang]['withdraw_methods'][2], TEXTS[lang]['withdraw_methods'][3])
    markup.row(TEXTS[lang]['back_menu'])
    return markup

def language_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("English 🇬🇧", "العربية 🇸🇦")
    return markup

# Command handlers
@bot.message_handler(commands=['start', 'restart'])
def start_command(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "None"
        full_name = message.from_user.first_name or ""
        if message.from_user.last_name:
            full_name += f" {message.from_user.last_name}"

        # Check if user exists and has language set
        c.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        
        if not user:
            # New user - ask for language
            msg = bot.send_message(message.chat.id, 
                                 "Please choose your language / يرجى اختيار اللغة", 
                                 reply_markup=language_markup())
            bot.register_next_step_handler(msg, process_language_choice)
            return
        else:
            # Existing user - proceed normally
            if not check_subscription(user_id):
                show_subscription_alert(message)
                return

            # Register/update user
            code = generate_code(user_id)
            c.execute("""
                INSERT OR IGNORE INTO users (user_id, username, full_name, code) 
                VALUES (?, ?, ?, ?)
                """, (user_id, username, full_name, code))
            
            c.execute("""
                UPDATE users SET 
                username = ?, 
                full_name = ?,
                last_active = ?
                WHERE user_id = ?
                """, (username, full_name, datetime.now(), user_id))
            
            conn.commit()
            show_main_menu(message)
            update_user_activity(user_id)
        
    except Exception as e:
        logging.error(f"Start command error: {e}")
        bot.send_message(message.chat.id, 
                        get_text('error', user_id),
                        reply_markup=types.ReplyKeyboardRemove())

def process_language_choice(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "None"
        full_name = message.from_user.first_name or ""
        if message.from_user.last_name:
            full_name += f" {message.from_user.last_name}"
            
        if "عرب" in message.text or "Arab" in message.text:
            language = 'ar'
        else:
            language = 'en'
            
        # Register new user with language
        code = generate_code(user_id)
        c.execute("""
            INSERT OR REPLACE INTO users (user_id, username, full_name, code, language) 
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, full_name, code, language))
        conn.commit()
        
        if not check_subscription(user_id):
            show_subscription_alert(message)
        else:
            show_main_menu(message)
            
    except Exception as e:
        logging.error(f"Language choice error: {e}")
        bot.send_message(message.chat.id, 
                        "Error occurred, please try again / حدث خطأ، يرجى المحاولة مرة أخرى",
                        reply_markup=types.ReplyKeyboardRemove())

def show_subscription_alert(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    for channel in CHANNELS:
        markup.add(types.InlineKeyboardButton(f"Join {channel}", url=f"https://t.me/{channel.strip('@')}"))
    markup.add(types.InlineKeyboardButton(get_text('subscription_done', user_id), callback_data="check_sub"))
    bot.send_message(message.chat.id, get_text('not_subscribed', user_id), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_subscription_callback(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, get_text('subscription_alert', user_id), show_alert=True)

@bot.message_handler(func=lambda message: message.text in [
    TEXTS['en']['main_menu'][0], TEXTS['ar']['main_menu'][0]  # Buy Referral Code
])
def handle_purchase_request(message):
    try:
        user_id = message.from_user.id
        c.execute("SELECT has_purchased FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        if result and result[0] == 1:
            code = generate_code(user_id)
            referral_link = f"https://t.me/{bot.get_me().username}?start={code}"
            bot.send_message(
                message.chat.id,
                get_text('already_purchased', user_id, link=referral_link),
                reply_markup=main_menu_markup(user_id)
            )
            return
        
        bot.send_message(
            message.chat.id,
            get_text('purchase_info', user_id),
            reply_markup=payment_methods_markup(user_id)
        )
        update_user_activity(user_id)
        
    except Exception as e:
        logging.error(f"Purchase request error: {e}")
        bot.send_message(
            message.chat.id,
            get_text('error', user_id),
            reply_markup=main_menu_markup(user_id)
        )

@bot.message_handler(func=lambda message: message.text in [
    TEXTS['en']['payment_methods'][0], TEXTS['ar']['payment_methods'][0],  # AsiaCell
    TEXTS['en']['payment_methods'][1], TEXTS['ar']['payment_methods'][1]  # Zain Iraq
])
def handle_payment_method(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    if message.text in [TEXTS['en']['payment_methods'][0], TEXTS['ar']['payment_methods'][0]]:
        method = "asiacell"
        method_text = TEXTS[lang]['payment_methods'][0]
    else:
        method = "zain"
        method_text = TEXTS[lang]['payment_methods'][1]
        
    msg = bot.send_message(message.chat.id,
                          get_text('enter_phone', user_id, method=method_text),
                          reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda m: process_payment(m, method))

def process_payment(message, method):
    try:
        user_id = message.from_user.id
        phone = message.text.strip()
        
        if not phone.isdigit() or len(phone) < 8:
            bot.send_message(message.chat.id, get_text('invalid_phone', user_id), reply_markup=main_menu_markup(user_id))
            return
        
        # Register payment request
        c.execute("INSERT INTO payment_requests (user_id, phone_number, amount, payment_method) VALUES (?, ?, ?, ?)",
                 (user_id, phone, 2.0, method))
        
        # Send approval request to admin
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        )
        
        admin_msg = (f"📌 New referral code purchase:\n\n"
                    f"👤 User: {get_user_info(user_id)}\n"
                    f"📱 Phone: {phone}\n"
                    f"💳 Method: {'AsiaCell' if method == 'asiacell' else 'Zain Iraq'}\n"
                    f"🆔 User Code: {generate_code(user_id)}")
        
        bot.send_message(ORDER_CHANNEL, admin_msg, reply_markup=markup)
        bot.send_message(user_id, get_text('payment_request_sent', user_id), reply_markup=main_menu_markup(user_id))
        conn.commit()
    except Exception as e:
        logging.error(f"Payment processing error: {e}")
        bot.send_message(message.chat.id, get_text('error', user_id), reply_markup=main_menu_markup(user_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_admin_decision(call):
    try:
        action, user_id = call.data.split("_")
        user_id = int(user_id)
        
        if action == "approve":
            # Activate user's referral code
            c.execute("UPDATE users SET has_purchased = 1 WHERE user_id = ?", (user_id,))
            
            # Create referral link
            code = generate_code(user_id)
            referral_link = f"https://t.me/{bot.get_me().username}?start={code}"
            
            # Notify user
            try:
                bot.send_message(user_id,
                                get_text('payment_approved', user_id, link=referral_link),
                                reply_markup=main_menu_markup(user_id))
            except Exception as e:
                logging.error(f"Message sending failed: {e}")
            
            bot.answer_callback_query(call.id, "Request approved")
        else:
            # Reject request
            try:
                bot.send_message(user_id,
                               get_text('payment_rejected', user_id),
                               reply_markup=main_menu_markup(user_id))
            except Exception as e:
                logging.error(f"Message sending failed: {e}")
            
            bot.answer_callback_query(call.id, "Request rejected")
        
        # Update request status
        c.execute("UPDATE payment_requests SET status = ? WHERE user_id = ? AND status = 'pending'",
                 (action + 'd', user_id))
        conn.commit()
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        logging.error(f"Admin decision error: {e}")

@bot.message_handler(func=lambda message: message.text in [
    TEXTS['en']['main_menu'][1], TEXTS['ar']['main_menu'][1]  # Withdraw Earnings
])
def handle_withdraw_request(message):
    try:
        user_id = message.from_user.id
        balance = get_user_balance(user_id)
        
        if balance < 2.0:
            bot.send_message(message.chat.id,
                            get_text('min_withdraw', user_id),
                            reply_markup=main_menu_markup(user_id))
            return
        
        msg = bot.send_message(message.chat.id,
                             get_text('verify_code', user_id),
                             reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, verify_withdraw_code)
        
    except Exception as e:
        logging.error(f"Withdrawal request error: {e}")
        bot.send_message(message.chat.id,
                        get_text('error', user_id),
                        reply_markup=main_menu_markup(user_id))

def verify_withdraw_code(message):
    try:
        user_id = message.from_user.id
        user_code = generate_code(user_id)
        
        if message.text.strip() == user_code:
            bot.send_message(message.chat.id,
                           get_text('choose_withdraw', user_id),
                           reply_markup=withdraw_methods_markup(user_id))
        else:
            bot.send_message(message.chat.id,
                           get_text('invalid_code', user_id),
                           reply_markup=main_menu_markup(user_id))
            
    except Exception as e:
        logging.error(f"Withdrawal verification error: {e}")
        bot.send_message(message.chat.id,
                        get_text('error', user_id),
                        reply_markup=main_menu_markup(user_id))

@bot.message_handler(func=lambda message: message.text in [
    TEXTS['en']['withdraw_methods'][0], TEXTS['ar']['withdraw_methods'][0],  # Zain Iraq
    TEXTS['en']['withdraw_methods'][1], TEXTS['ar']['withdraw_methods'][1],  # AsiaCell
    TEXTS['en']['withdraw_methods'][2], TEXTS['ar']['withdraw_methods'][2],  # MasterCard/KNet
    TEXTS['en']['withdraw_methods'][3], TEXTS['ar']['withdraw_methods'][3]   # Crypto
])
def handle_withdraw_method(message):
    try:
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        
        method_mapping = {
            TEXTS[lang]['withdraw_methods'][0]: "zain",
            TEXTS[lang]['withdraw_methods'][1]: "asiacell",
            TEXTS[lang]['withdraw_methods'][2]: "card",
            TEXTS[lang]['withdraw_methods'][3]: "crypto"
        }
        
        method = method_mapping[message.text]
        method_text = message.text
        
        msg = bot.send_message(message.chat.id,
                             get_text('enter_withdraw_details', user_id, method=method_text),
                             reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, lambda m: process_withdraw(m, method))
        
    except Exception as e:
        logging.error(f"Withdrawal method error: {e}")
        bot.send_message(message.chat.id,
                        get_text('error', user_id),
                        reply_markup=main_menu_markup(user_id))

def process_withdraw(message, method):
    try:
        user_id = message.from_user.id
        account_info = message.text.strip()
        balance = get_user_balance(user_id)
        
        # Validate info based on method
        if method in ["zain", "asiacell"] and not account_info.isdigit():
            bot.send_message(message.chat.id,
                           get_text('invalid_phone', user_id),
                           reply_markup=main_menu_markup(user_id))
            return
        
        # Register withdrawal request
        c.execute("INSERT INTO withdrawal_requests (user_id, amount, method, account_info) VALUES (?, ?, ?, ?)",
                 (user_id, balance, method, account_info))
        
        # Deduct from user balance
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?",
                 (balance, user_id))
        
        # Notify admin
        admin_msg = (f"📌 New withdrawal request:\n\n"
                    f"👤 User: {get_user_info(user_id)}\n"
                    f"💵 Amount: {balance:.2f}$\n"
                    f"💳 Method: {method}\n"
                    f"📝 Info: {account_info}")
        
        bot.send_message(ORDER_CHANNEL, admin_msg)
        
        # Notify user
        bot.send_message(message.chat.id,
                       get_text('withdraw_request_sent', user_id),
                       reply_markup=main_menu_markup(user_id))
        
        conn.commit()
        
    except Exception as e:
        logging.error(f"Withdrawal processing error: {e}")
        bot.send_message(message.chat.id,
                        get_text('error', user_id),
                        reply_markup=main_menu_markup(user_id))

@bot.message_handler(func=lambda message: message.text in [
    TEXTS['en']['main_menu'][2], TEXTS['ar']['main_menu'][2]  # My Stats
])
def handle_user_stats(message):
    try:
        user_id = message.from_user.id
        
        # Get user data
        c.execute("""
            SELECT balance, referrals, has_purchased, joined_date 
            FROM users WHERE user_id = ?
            """, (user_id,))
        result = c.fetchone()
        
        if not result:
            bot.send_message(message.chat.id,
                           get_text('error', user_id),
                           reply_markup=main_menu_markup(user_id))
            return
            
        balance, referrals, has_purchased, join_date = result
        
        # Calculate total referrals
        c.execute("SELECT COUNT(*) FROM referral_logs WHERE referrer_id = ?", (user_id,))
        total_refs = c.fetchone()[0]
        
        status = get_text('payment_approved', user_id).split(':')[0] if has_purchased else get_text('payment_rejected', user_id).split(':')[0]
        
        # Prepare stats message
        stats_msg = get_text('stats', user_id, 
                           balance=balance, 
                           refs=referrals, 
                           total_refs=total_refs,
                           join_date=join_date[:10],
                           status=status)
        
        bot.send_message(message.chat.id,
                       stats_msg,
                       reply_markup=main_menu_markup(user_id))
        
    except Exception as e:
        logging.error(f"Stats display error: {e}")
        bot.send_message(message.chat.id,
                        get_text('error', user_id),
                        reply_markup=main_menu_markup(user_id))

@bot.message_handler(func=lambda message: message.text in [
    TEXTS['en']['main_menu'][3], TEXTS['ar']['main_menu'][3]  # Refresh Data
])
def handle_refresh(message):
    try:
        user_id = message.from_user.id
        update_user_activity(user_id)
        bot.send_message(message.chat.id,
                        get_text('refresh_success', user_id),
                        reply_markup=main_menu_markup(user_id))
    except Exception as e:
        logging.error(f"Refresh error: {e}")
        bot.send_message(message.chat.id,
                        get_text('error', user_id),
                        reply_markup=main_menu_markup(user_id))

@bot.message_handler(func=lambda message: message.text in [
    TEXTS['en']['back_menu'], TEXTS['ar']['back_menu']  # Back to Main Menu
])
def handle_back_to_main(message):
    show_main_menu(message)

def show_main_menu(message):
    try:
        user_id = message.from_user.id
        update_user_activity(user_id)
        
        # Get user data
        c.execute("SELECT balance, referrals, has_purchased FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        if not result:
            bot.send_message(message.chat.id,
                           get_text('error', user_id),
                           reply_markup=types.ReplyKeyboardRemove())
            return
            
        balance, referrals, has_purchased = result
        
        # Prepare welcome message
        welcome_msg = get_text('start', user_id, 
                             name=get_user_info(user_id),
                             balance=balance,
                             refs=referrals)
        
        bot.send_message(message.chat.id,
                       welcome_msg,
                       reply_markup=main_menu_markup(user_id))
        
    except Exception as e:
        logging.error(f"Main menu error: {e}")
        bot.send_message(message.chat.id,
                        get_text('error', user_id),
                        reply_markup=types.ReplyKeyboardRemove())

# Flask routes
@app.route('/' + TOKEN, methods=['POST'])
def bot_webhook():
    try:
        json_data = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return "Error", 500

@app.route('/')
def set_webhook():
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g')
        return "Webhook is set!", 200
    except Exception as e:
        logging.error(f"Webhook setup error: {e}")
        return "Webhook setup failed", 500

if __name__ == '__main__':
    try:
        print("🚀 Bot is running...")
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g')
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:
        logging.error(f"Main error: {e}")
