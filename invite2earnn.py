from flask import Flask, request
from threading import Thread
import telebot
from telebot import types
import sqlite3
import time
import logging
from datetime import datetime
import random

# Initialize app
app = Flask(__name__)
TOKEN = '7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g'
CHANNELS = ["@intearnn", "@s111sgrh"]  # Required channels
ORDER_CHANNEL = "@intorders"
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"
bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)

# Mixed English/Arabic texts
TEXTS = {
    'welcome': "🌟 Welcome {name} | أهلاً بك {name} 🌟\n\n💰 Balance/Raqid: ${balance:.2f}\n👥 Referrals/إحالات: {refs}",
    'not_subscribed': "⚠️ Join our channels first | انضم لقنواتنا أولاً:\n{channels}",
    'subscription_done': "✅ Done | تم",
    'main_menu': [
        "💳 Buy Code/شراء كود", 
        "💰 Withdraw/سحب", 
        "📊 Stats/إحصائيات", 
        "🔄 Refresh/تحديث"
    ],
    'payment_methods': [
        "💳 AsiaCell/آسيا سيل", 
        "💳 Zain Iraq/زين العراق"
    ],
    'withdraw_methods': [
        "💳 Zain Iraq/زين العراق", 
        "💳 AsiaCell/آسيا سيل",
        "💳 Card/بطاقة", 
        "💳 Crypto/كريبتو"
    ],
    'back_menu': "🔙 Main Menu/القائمة",
    'already_purchased': "🎉 You already have a code! | لديك كود بالفعل!\n\n🔗 Your link:\n{link}\n\n💰 Earn $0.10 per referral | اربح 0.10$ لكل إحالة",
    'purchase_info': "💳 Buy referral code | شراء كود إحالة\n\n💰 Price/Sa'er: $2\n🔗 Earn $0.10 per referral | اربح 0.10$ لكل إحالة\n\nChoose payment method | اختر طريقة الدفع:",
    'enter_phone': "📱 Send your phone number | أرسل رقمك:\n(Must have $2 balance | يجب أن يحتوي على 2$)",
    'invalid_phone': "❌ Invalid number | رقم غير صحيح",
    'payment_request_sent': "📬 Request received | تم استلام الطلب\n⏳ Under review | قيد المراجعة",
    'payment_approved': "🎉 Code activated! | تم تفعيل الكود!\n\n🔗 Your link:\n{link}\n\n💰 Earn $0.10 per referral | اربح 0.10$ لكل إحالة",
    'payment_rejected': "❌ Request rejected | تم الرفض\nPlease try again | حاول لاحقاً",
    'min_withdraw': "❗ Minimum $2 to withdraw | الحد الأدنى 2$\nGet more referrals | احصل على المزيد من الإحالات",
    'verify_code': "🔐 Enter your code | أدخل كودك:",
    'invalid_code': "❌ Wrong code | كود خاطئ",
    'choose_withdraw': "💸 Choose method | اختر طريقة:",
    'enter_withdraw_details': "📤 Send {method} details | أرسل بيانات {method}:",
    'withdraw_request_sent': "✅ Request sent | تم الإرسال\n⏳ Processing in 24h | جاري المعالجة",
    'stats': "📊 Your stats | إحصائياتك:\n\n💰 Balance/Raqid: ${balance:.2f}\n👥 Active referrals/إحالات نشطة: {refs}\n🔗 Total referrals/مجموع الإحالات: {total_refs}\n📅 Joined/انضم في: {join_date}\n🔑 Status/حالة: {status}",
    'refresh_success': "🔄 Refreshed | تم التحديث",
    'error': "❌ Error | خطأ\nTry again | حاول لاحقاً",
    'referral_bonus': "🎊 New referral! | إحالة جديدة!\n+$0.10 added to your balance | تم إضافة 0.10$ لرصيدك",
    'referral_welcome': "👋 You joined via {name}'s link | انضمتم عبر رابط {name}\n💰 They earned $0.10 | لقد ربحوا 0.10$"
}

# Enhanced database setup
def init_db():
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    
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
        referrer_id INTEGER DEFAULT NULL
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS referral_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER UNIQUE,
        reward_claimed BOOLEAN DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(referrer_id) REFERENCES users(user_id),
        FOREIGN KEY(referred_id) REFERENCES users(user_id)
    )''')
    
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
def generate_code(user_id):
    return f"REF{user_id}_{int(time.time())}"

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

def process_referral(referrer_id, referred_id):
    try:
        # Check if this referral already exists
        c.execute("SELECT 1 FROM referral_logs WHERE referred_id = ?", (referred_id,))
        if c.fetchone():
            return False
        
        # Add referral record
        c.execute("INSERT INTO referral_logs (referrer_id, referred_id) VALUES (?, ?)",
                 (referrer_id, referred_id))
        
        # Update referrer's stats and balance
        c.execute("UPDATE users SET balance = balance + 0.10, referrals = referrals + 1 WHERE user_id = ?",
                 (referrer_id,))
        
        # Update referred user's referrer_id
        c.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?",
                 (referrer_id, referred_id))
        
        conn.commit()
        
        # Notify referrer
        try:
            bot.send_message(referrer_id, TEXTS['referral_bonus'])
        except:
            pass
            
        return True
    except Exception as e:
        logging.error(f"Referral processing error: {e}")
        return False

# Keyboard Markups
def main_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row(TEXTS['main_menu'][0], TEXTS['main_menu'][1])
    markup.row(TEXTS['main_menu'][2], TEXTS['main_menu'][3])
    return markup

def payment_methods_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row(TEXTS['payment_methods'][0], TEXTS['payment_methods'][1])
    markup.row(TEXTS['back_menu'])
    return markup

def withdraw_methods_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row(TEXTS['withdraw_methods'][0], TEXTS['withdraw_methods'][1])
    markup.row(TEXTS['withdraw_methods'][2], TEXTS['withdraw_methods'][3])
    markup.row(TEXTS['back_menu'])
    return markup

def subscription_markup():
    markup = types.InlineKeyboardMarkup()
    for channel in CHANNELS:
        markup.add(types.InlineKeyboardButton(f"Join {channel}", url=f"https://t.me/{channel.strip('@')}"))
    markup.add(types.InlineKeyboardButton(TEXTS['subscription_done'], callback_data="check_sub"))
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

        # Check for referral code
        referral_code = None
        if len(message.text.split()) > 1:
            referral_code = message.text.split()[1]

        # Check subscription
        if not check_subscription(user_id):
            channels = "\n".join(CHANNELS)
            bot.send_message(message.chat.id, 
                           TEXTS['not_subscribed'].format(channels=channels),
                           reply_markup=subscription_markup())
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
        
        # Process referral if exists
        if referral_code:
            try:
                # Extract referrer_id from code (REF12345_timestamp)
                referrer_id = int(referral_code[3:].split('_')[0])
                if referrer_id != user_id:  # Prevent self-referral
                    if process_referral(referrer_id, user_id):
                        referrer_name = get_user_info(referrer_id)
                        bot.send_message(user_id, 
                                        TEXTS['referral_welcome'].format(name=referrer_name))
            except Exception as e:
                logging.error(f"Referral processing error: {e}")
        
        show_main_menu(message)
        update_user_activity(user_id)
        
    except Exception as e:
        logging.error(f"Start command error: {e}")
        bot.send_message(message.chat.id, 
                       TEXTS['error'],
                       reply_markup=types.ReplyKeyboardRemove())

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_subscription_callback(call):
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "❗ Join all channels first | انضم لجميع القنوات أولاً", show_alert=True)

@bot.message_handler(func=lambda message: message.text == TEXTS['main_menu'][0])
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
                TEXTS['already_purchased'].format(link=referral_link),
                reply_markup=main_menu_markup()
            )
            return
        
        bot.send_message(
            message.chat.id,
            TEXTS['purchase_info'],
            reply_markup=payment_methods_markup()
        )
        update_user_activity(user_id)
        
    except Exception as e:
        logging.error(f"Purchase request error: {e}")
        bot.send_message(
            message.chat.id,
            TEXTS['error'],
            reply_markup=main_menu_markup()
        )

@bot.message_handler(func=lambda message: message.text in TEXTS['payment_methods'])
def handle_payment_method(message):
    method = message.text
    msg = bot.send_message(message.chat.id,
                          TEXTS['enter_phone'],
                          reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda m: process_payment(m, method))

def process_payment(message, method):
    try:
        user_id = message.from_user.id
        phone = message.text.strip()
        
        if not phone.isdigit() or len(phone) < 8:
            bot.send_message(message.chat.id, TEXTS['invalid_phone'], reply_markup=main_menu_markup())
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
                    f"💳 Method: {method}\n"
                    f"🆔 User Code: {generate_code(user_id)}")
        
        bot.send_message(ORDER_CHANNEL, admin_msg, reply_markup=markup)
        bot.send_message(user_id, TEXTS['payment_request_sent'], reply_markup=main_menu_markup())
        conn.commit()
    except Exception as e:
        logging.error(f"Payment processing error: {e}")
        bot.send_message(message.chat.id, TEXTS['error'], reply_markup=main_menu_markup())

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
                              TEXTS['payment_approved'].format(link=referral_link),
                              reply_markup=main_menu_markup())
            except Exception as e:
                logging.error(f"Message sending failed: {e}")
            
            bot.answer_callback_query(call.id, "Request approved")
        else:
            # Reject request
            try:
                bot.send_message(user_id,
                              TEXTS['payment_rejected'],
                              reply_markup=main_menu_markup())
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

@bot.message_handler(func=lambda message: message.text == TEXTS['main_menu'][1])
def handle_withdraw_request(message):
    try:
        user_id = message.from_user.id
        balance = get_user_balance(user_id)
        
        if balance < 2.0:
            bot.send_message(message.chat.id,
                           TEXTS['min_withdraw'],
                           reply_markup=main_menu_markup())
            return
        
        msg = bot.send_message(message.chat.id,
                             TEXTS['verify_code'],
                             reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, verify_withdraw_code)
        
    except Exception as e:
        logging.error(f"Withdrawal request error: {e}")
        bot.send_message(message.chat.id,
                        TEXTS['error'],
                        reply_markup=main_menu_markup())

def verify_withdraw_code(message):
    try:
        user_id = message.from_user.id
        user_code = generate_code(user_id)
        
        if message.text.strip() == user_code:
            bot.send_message(message.chat.id,
                           TEXTS['choose_withdraw'],
                           reply_markup=withdraw_methods_markup())
        else:
            bot.send_message(message.chat.id,
                           TEXTS['invalid_code'],
                           reply_markup=main_menu_markup())
            
    except Exception as e:
        logging.error(f"Withdrawal verification error: {e}")
        bot.send_message(message.chat.id,
                       TEXTS['error'],
                       reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text in TEXTS['withdraw_methods'])
def handle_withdraw_method(message):
    try:
        method = message.text
        msg = bot.send_message(message.chat.id,
                             TEXTS['enter_withdraw_details'].format(method=method),
                             reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, lambda m: process_withdraw(m, method))
        
    except Exception as e:
        logging.error(f"Withdrawal method error: {e}")
        bot.send_message(message.chat.id,
                       TEXTS['error'],
                       reply_markup=main_menu_markup())

def process_withdraw(message, method):
    try:
        user_id = message.from_user.id
        account_info = message.text.strip()
        balance = get_user_balance(user_id)
        
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
                       TEXTS['withdraw_request_sent'],
                       reply_markup=main_menu_markup())
        
        conn.commit()
        
    except Exception as e:
        logging.error(f"Withdrawal processing error: {e}")
        bot.send_message(message.chat.id,
                       TEXTS['error'],
                       reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == TEXTS['main_menu'][2])
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
                           TEXTS['error'],
                           reply_markup=main_menu_markup())
            return
            
        balance, referrals, has_purchased, join_date = result
        
        # Calculate total referrals
        c.execute("SELECT COUNT(*) FROM referral_logs WHERE referrer_id = ?", (user_id,))
        total_refs = c.fetchone()[0]
        
        status = "Active/نشط" if has_purchased else "Inactive/غير نشط"
        
        # Prepare stats message
        stats_msg = TEXTS['stats'].format(
            balance=balance,
            refs=referrals,
            total_refs=total_refs,
            join_date=join_date[:10],
            status=status
        )
        
        bot.send_message(message.chat.id,
                       stats_msg,
                       reply_markup=main_menu_markup())
        
    except Exception as e:
        logging.error(f"Stats display error: {e}")
        bot.send_message(message.chat.id,
                       TEXTS['error'],
                       reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == TEXTS['main_menu'][3])
def handle_refresh(message):
    try:
        user_id = message.from_user.id
        update_user_activity(user_id)
        bot.send_message(message.chat.id,
                       TEXTS['refresh_success'],
                       reply_markup=main_menu_markup())
    except Exception as e:
        logging.error(f"Refresh error: {e}")
        bot.send_message(message.chat.id,
                       TEXTS['error'],
                       reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == TEXTS['back_menu'])
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
                           TEXTS['error'],
                           reply_markup=types.ReplyKeyboardRemove())
            return
            
        balance, referrals, has_purchased = result
        
        # Prepare welcome message
        welcome_msg = TEXTS['welcome'].format(
            name=get_user_info(user_id),
            balance=balance,
            refs=referrals
        )
        
        bot.send_message(message.chat.id,
                       welcome_msg,
                       reply_markup=main_menu_markup())
        
    except Exception as e:
        logging.error(f"Main menu error: {e}")
        bot.send_message(message.chat.id,
                       TEXTS['error'],
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
