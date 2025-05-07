from flask import Flask, request
from threading import Thread
import telebot
from telebot import types
import sqlite3
import time
import logging
from datetime import datetime
import hashlib

# Initialize the app
app = Flask(__name__)
TOKEN = '7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g'
CHANNELS = ["@intearnn", "@s111sgrh"]  # Required channels
ORDER_CHANNEL = "@intorders"
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"  # Add admin ID here
bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)

# Arabic texts
TEXTS = {
    'start': "أهلاً بك {name} 👋\n\n💰 رصيدك الحالي: {balance:.2f}$\n👥 عدد الإحالات: {refs}\n\n📌 اختر من القائمة:",
    'not_subscribed': "⚠️ للبدء، يرجى الانضمام إلى قنواتنا:",
    'subscription_done': "✅ تم الاشتراك",
    'subscription_alert': "❗ لم تنضم لجميع القنوات",
    'main_menu': ["💳 شراء كود إحالة", "💰 سحب الأرباح", "📊 إحصائياتي", "🔄 تحديث البيانات"],
    'back_menu': "🔙 القائمة الرئيسية",
    'payment_methods': ["💳 آسيا سيل", "💳 زين العراق"],
    'withdraw_methods': ["💳 زين العراق", "💳 آسيا سيل", "💳 ماستركارد/كي نت", "💳 كريبتو"],
    'already_purchased': "✅ لديك بالفعل كود إحالة نشط\n\n🔗 يمكنك مشاركة هذا الرابط:\n{link}\n\n💰 ستربح 0.1$ لكل إحالة جديدة",
    'purchase_info': "💳 لشراء كود الإحالة:\n\n🚀 ارفق رقم رصيد 2$ فعّال لشراء كود الاستثمار الخاص بك\n💰 للربح عبر مشاركته فقط 0.10$ لكل شخص\n\n📌 سيتم التحقق تلقائياً من رصيد الرقم المرفق\n❌ أي خطأ بالرصيد سيؤدي لرفض العملية",
    'enter_phone': "🔔 طريقة الدفع: {method}\n\n📌 ارفق رقم رصيد 2$ فعّال لشراء كود الإحالة:",
    'invalid_phone': "❌ رقم غير صحيح، يرجى المحاولة مرة أخرى",
    'payment_request_sent': "📬 تم استلام طلبك، قيد المراجعة...",
    'payment_approved': "🎉 تم تفعيل كود الإحالة الخاص بك!\n\n🔗 رابط الإحالة:\n{link}\n\n💰 اربح 0.1$ لكل اشتراك عبر رابطك\n\n📌 شارك هذا الرابط لبدء الربح",
    'payment_rejected': "❌ تم رفض طلبك، يرجى التحقق من المعلومات والمحاولة لاحقاً",
    'min_withdraw': "❗ الحد الأدنى للسحب هو 2$\n\nيمكنك زيادة رصيدك عن طريق:\n- الحصول على المزيد من الإحالات\n- شراء رموز إحالة إضافية",
    'verify_code': "📤 لسحب الأرباح:\n\nكود التحقق الخاص بك: {code}\n\nيرجى إرسال كود التحقق هذا لتأكيد السحب:",
    'invalid_code': "❌ كود التحقق غير صحيح",
    'choose_withdraw': "💰 اختر طريقة السحب:",
    'enter_withdraw_details': "📤 يرجى إرسال تفاصيل {method}:",
    'withdraw_request_sent': "✅ تم استلام طلب السحب\n\n⏳ جاري المعالجة خلال 24 ساعة\n📌 سيتم إعلامك عند الانتهاء",
    'stats': "📊 إحصائياتك:\n\n💰 الرصيد الحالي: {balance:.2f}$\n👥 الإحالات النشطة: {refs}\n🔗 إجمالي الإحالات: {total_refs}\n📅 تاريخ الانضمام: {join_date}\n🔑 كود الإحالة: {status}",
    'refresh_success': "✅ تم تحديث البيانات بنجاح",
    'error': "❌ حدث خطأ، يرجى المحاولة لاحقاً",
    'new_referral': "🎉 حصلت على 0.10$ مقابل إحالة جديدة!\n\n👤 المستخدم: {user}\n💰 رصيدك الجديد: {balance:.2f}$"
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
        withdraw_code TEXT UNIQUE,
        balance REAL DEFAULT 0.0,
        free_referrals INTEGER DEFAULT 0,
        paid_referrals INTEGER DEFAULT 0,
        has_purchased BOOLEAN DEFAULT 0,
        joined_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_active DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Referrals tracking table
    c.execute('''CREATE TABLE IF NOT EXISTS referral_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER UNIQUE,
        is_paid BOOLEAN DEFAULT 0,
        reward_claimed BOOLEAN DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(referrer_id) REFERENCES users(user_id),
        FOREIGN KEY(referred_id) REFERENCES users(user_id)
    )''')
    
    # Payment tracking table
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
    
    # Withdrawal tracking table
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
    return f"PAID_{user_id}_{int(time.time())}"

def generate_withdraw_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()

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

def get_withdraw_code(user_id):
    c.execute("SELECT withdraw_code FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if result and result[0]:
        return result[0]
    else:
        code = generate_withdraw_code(user_id)
        c.execute("UPDATE users SET withdraw_code = ? WHERE user_id = ?", (code, user_id))
        conn.commit()
        return code

# Keyboards
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

# Command handlers
@bot.message_handler(commands=['start', 'restart'])
def start_command(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "None"
        full_name = message.from_user.first_name or ""
        if message.from_user.last_name:
            full_name += f" {message.from_user.last_name}"

        # Check for referral link
        referral_code = None
        if len(message.text.split()) > 1:
            referral_code = message.text.split()[1]

        # Check subscription
        if not check_subscription(user_id):
            show_subscription_alert(message)
            return

        # Register/update user
        code = generate_code(user_id)
        withdraw_code = generate_withdraw_code(user_id)
        c.execute("""
            INSERT OR IGNORE INTO users (user_id, username, full_name, code, withdraw_code) 
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, full_name, code, withdraw_code))
        
        c.execute("""
            UPDATE users SET 
            username = ?, 
            full_name = ?,
            last_active = ?,
            withdraw_code = COALESCE(withdraw_code, ?)
            WHERE user_id = ?
            """, (username, full_name, datetime.now(), withdraw_code, user_id))
        
        # Process referral if exists
        if referral_code:
            try:
                # Verify referral code format
                if not referral_code.startswith("PAID_") or len(referral_code.split('_')) < 2:
                    raise ValueError("Invalid referral code format")
                
                referrer_id = int(referral_code.split('_')[1])
                
                # Check if this is a self-referral
                if referrer_id == user_id:
                    raise ValueError("Self-referral not allowed")
                
                # Check if user was already referred
                c.execute("SELECT 1 FROM referral_logs WHERE referred_id = ?", (user_id,))
                if c.fetchone():
                    raise ValueError("User already referred")
                
                # Check if referrer exists and has purchased code
                c.execute("SELECT has_purchased FROM users WHERE user_id = ?", (referrer_id,))
                referrer_data = c.fetchone()
                if not referrer_data:
                    raise ValueError("Referrer not found")
                
                has_purchased = referrer_data[0]
                
                # Log referral
                c.execute("INSERT OR IGNORE INTO referral_logs (referrer_id, referred_id, is_paid) VALUES (?, ?, ?)",
                         (referrer_id, user_id, has_purchased))
                
                # Add reward to referrer only if they have purchased
                if has_purchased:
                    c.execute("UPDATE users SET balance = balance + 0.1, paid_referrals = paid_referrals + 1 WHERE user_id = ?",
                             (referrer_id,))
                else:
                    c.execute("UPDATE users SET free_referrals = free_referrals + 1 WHERE user_id = ?",
                             (referrer_id,))
                
                # Notify referrer if they have purchased
                if has_purchased:
                    try:
                        bot.send_message(referrer_id, 
                                       TEXTS['new_referral'].format(
                                           user=get_user_info(user_id),
                                           balance=get_user_balance(referrer_id)
                                       ))
                    except:
                        pass
                
            except Exception as e:
                logging.error(f"Referral processing error: {e}")

        conn.commit()
        show_main_menu(message)
        update_user_activity(user_id)
        
    except Exception as e:
        logging.error(f"Start command error: {e}")
        bot.send_message(message.chat.id, 
                        TEXTS['error'],
                        reply_markup=main_menu_markup())

def show_subscription_alert(message):
    markup = types.InlineKeyboardMarkup()
    for channel in CHANNELS:
        markup.add(types.InlineKeyboardButton(f"Join {channel}", url=f"https://t.me/{channel.strip('@')}"))
    markup.add(types.InlineKeyboardButton(TEXTS['subscription_done'], callback_data="check_sub"))
    bot.send_message(message.chat.id, TEXTS['not_subscribed'], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_subscription_callback(call):
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, TEXTS['subscription_alert'], show_alert=True)

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
    method = "asiacell" if "آسيا" in message.text else "zain"
    method_text = message.text
    
    msg = bot.send_message(message.chat.id,
                          TEXTS['enter_phone'].format(method=method_text),
                          reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda m: process_payment(m, method))

def process_payment(message, method):
    try:
        user_id = message.from_user.id
        phone = message.text.strip()
        
        if not phone.isdigit() or len(phone) < 8:
            bot.send_message(message.chat.id, TEXTS['invalid_phone'], reply_markup=main_menu_markup())
            return
        
        # Simulate balance check (in reality you'd need API integration)
        has_sufficient_balance = True  # Default for demo
        
        if not has_sufficient_balance:
            bot.send_message(message.chat.id,
                           "❌ الرصيد غير كافي! يرجى استخدام رقم به رصيد 2$ على الأقل",
                           reply_markup=main_menu_markup())
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
        
        admin_msg = (f"📌 New referral code purchase request:\n\n"
                    f"👤 User: {get_user_info(user_id)}\n"
                    f"📱 Phone: {phone}\n"
                    f"💳 Method: {method}\n"
                    f"💰 Balance: Sufficient (simulated)\n"
                    f"🆔 User code: {generate_code(user_id)}")
        
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
            # Activate referral code for user
            code = generate_code(user_id)
            c.execute("UPDATE users SET has_purchased = 1 WHERE user_id = ?", (user_id,))
            
            # Create referral link
            referral_link = f"https://t.me/{bot.get_me().username}?start={code}"
            
            # Send code to channel
            bot.send_message(ORDER_CHANNEL, 
                           f"🆔 New referral code:\n\n👤 User: {get_user_info(user_id)}\n🔑 Code: {code}\n🔗 Link: {referral_link}")
            
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
                 ('approved' if action == 'approve' else 'rejected', user_id))
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
        
        # Generate and display withdraw code
        withdraw_code = get_withdraw_code(user_id)
        msg = bot.send_message(message.chat.id,
                             TEXTS['verify_code'].format(code=withdraw_code),
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
        correct_code = get_withdraw_code(user_id)
        user_input = message.text.strip()
        
        if user_input == correct_code:
            # Generate new code after successful verification
            new_code = generate_withdraw_code(user_id)
            c.execute("UPDATE users SET withdraw_code = ? WHERE user_id = ?", (new_code, user_id))
            conn.commit()
            
            bot.send_message(message.chat.id,
                           TEXTS['choose_withdraw'],
                           reply_markup=withdraw_methods_markup())
        else:
            bot.send_message(message.chat.id,
                           TEXTS['invalid_code'],
                           reply_markup=main_menu_markup())
            
    except Exception as e:
        logging.error(f"Withdrawal code verification error: {e}")
        bot.send_message(message.chat.id,
                        TEXTS['error'],
                        reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text in TEXTS['withdraw_methods'])
def handle_withdraw_method(message):
    try:
        method_mapping = {
            TEXTS['withdraw_methods'][0]: "zain",
            TEXTS['withdraw_methods'][1]: "asiacell",
            TEXTS['withdraw_methods'][2]: "card",
            TEXTS['withdraw_methods'][3]: "crypto"
        }
        
        method = method_mapping[message.text]
        method_text = message.text
        
        msg = bot.send_message(message.chat.id,
                             TEXTS['enter_withdraw_details'].format(method=method_text),
                             reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, lambda m: process_withdraw(m, method))
        
    except Exception as e:
        logging.error(f"Withdrawal method selection error: {e}")
        bot.send_message(message.chat.id,
                        TEXTS['error'],
                        reply_markup=main_menu_markup())

def process_withdraw(message, method):
    try:
        user_id = message.from_user.id
        account_info = message.text.strip()
        balance = get_user_balance(user_id)
        
        # Validate info based on withdrawal method
        if method in ["zain", "asiacell"] and not account_info.isdigit():
            bot.send_message(message.chat.id,
                           TEXTS['invalid_phone'],
                           reply_markup=main_menu_markup())
            return
        
        # Register withdrawal request
        c.execute("INSERT INTO withdrawal_requests (user_id, amount, method, account_info) VALUES (?, ?, ?, ?)",
                 (user_id, balance, method, account_info))
        
        # Deduct from user balance
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?",
                 (balance, user_id))
        
        # Generate new withdraw code
        new_code = generate_withdraw_code(user_id)
        c.execute("UPDATE users SET withdraw_code = ? WHERE user_id = ?", (new_code, user_id))
        
        # Send notification to admin
        admin_msg = (f"📌 New withdrawal request:\n\n"
                    f"👤 User: {get_user_info(user_id)}\n"
                    f"💵 Amount: {balance:.2f}$\n"
                    f"💳 Method: {method}\n"
                    f"📝 Info: {account_info}\n"
                    f"🆔 Verification code: {new_code}")
        
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
            SELECT balance, free_referrals, paid_referrals, has_purchased, joined_date 
            FROM users WHERE user_id = ?
            """, (user_id,))
        result = c.fetchone()
        
        if not result:
            bot.send_message(message.chat.id,
                           TEXTS['error'],
                           reply_markup=main_menu_markup())
            return
            
        balance, free_refs, paid_refs, has_purchased, join_date = result
        
        # Calculate total referrals
        c.execute("SELECT COUNT(*) FROM referral_logs WHERE referrer_id = ?", (user_id,))
        total_refs = c.fetchone()[0]
        
        status = "✅ Active" if has_purchased else "❌ Inactive"
        
        # Prepare stats message
        stats_msg = TEXTS['stats'].format(
            balance=balance,
            refs=free_refs + paid_refs,
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
        c.execute("SELECT balance, free_referrals, paid_referrals FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        if not result:
            bot.send_message(message.chat.id,
                           TEXTS['error'],
                           reply_markup=types.ReplyKeyboardRemove())
            return
            
        balance, free_refs, paid_refs = result
        
        # Prepare welcome message
        welcome_msg = TEXTS['start'].format(
            name=get_user_info(user_id),
            balance=balance,
            refs=free_refs + paid_refs
        )
        
        bot.send_message(message.chat.id,
                       welcome_msg,
                       reply_markup=main_menu_markup())
        
    except Exception as e:
        logging.error(f"Main menu display error: {e}")
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
        return "Webhook setup successfully!", 200
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
