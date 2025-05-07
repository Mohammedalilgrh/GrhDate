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

# Arabic texts
TEXTS = {
    'welcome': "أهلاً بك {name} 👋\n\n💰 رصيدك الحالي: {balance:.2f}$\n👥 عدد الإحالات: {refs}\n\n📌 اختر من القائمة:",
    'not_subscribed': "⚠️ للبدء، يرجى الانضمام إلى قنواتنا:",
    'subscription_done': "✅ تم",
    'main_menu': [
        "💳 شراء كود إحالة", 
        "💰 سحب الأرباح", 
        "📊 إحصائياتي", 
        "🔄 تحديث البيانات"
    ],
    'payment_methods': [
        "💳 زين العراق", 
        "💳 آسيا سيل"
    ],
    'withdraw_methods': [
        "💳 زين العراق", 
        "💳 آسيا سيل",
        "💳 ماستركارد/كي نت", 
        "💳 كريبتو"
    ],
    'back_menu': "🔙 القائمة الرئيسية",
    'already_purchased': "🎉 لديك بالفعل كود إحالة نشط!\n\n🔗 يمكنك مشاركة هذا الرابط:\n{link}\n\n💰 ستربح 0.10$ لكل إحالة جديدة",
    'purchase_info': "💳 لشراء كود الإحالة:\n\n💰 السعر: 2$\n🔗 اربح 0.10$ لكل إحالة جديدة\n\nاختر طريقة الدفع:",
    'enter_card': "📌 ارسل رقم كرت رصيد فعّال ابو ال2$ لشراء كود الأستثمار الخاص بك\n\nسيتم التحقق من الكرت تلقائياً لتفعيل وارسال ♦️\nكود الاستثمار الخاص بك لتتمكن من الربح معنا",
    'invalid_card': "❌ رقم الكرت غير صحيح، يرجى المحاولة مرة أخرى",
    'payment_request_sent': "📬 تم استلام طلبك، قيد المراجعة...",
    'payment_approved': "🎉 تم تفعيل كود الإحالة الخاص بك!\n\n🔗 رابط الإحالة:\n{link}\n\n💰 اربح 0.10$ لكل اشتراك عبر رابطك\n\n📌 شارك هذا الرابط لبدء الربح",
    'payment_rejected': "❌ تم رفض طلبك، يرجى التحقق من المعلومات والمحاولة لاحقاً",
    'min_withdraw': "❗ الحد الأدنى للسحب هو 2$\n\nيمكنك زيادة رصيدك عن طريق:\n- الحصول على المزيد من الإحالات\n- شراء رموز إحالة إضافية",
    'verify_code': "📤 لسحب الأرباح:\n\nيرجى إرسال كود الإحالة الخاص بك للتحقق:",
    'invalid_code': "❌ كود التحقق غير صحيح",
    'choose_withdraw': "💰 اختر طريقة السحب:",
    'enter_withdraw_details': "📤 يرجى إرسال تفاصيل {method}:",
    'withdraw_request_sent': "✅ تم استلام طلب السحب\n\n⏳ جاري المعالجة خلال 24 ساعة\n📌 سيتم إعلامك عند الانتهاء",
    'stats': "📊 إحصائياتك:\n\n💰 الرصيد الحالي: {balance:.2f}$\n👥 الإحالات النشطة: {refs}\n🔗 إجمالي الإحالات: {total_refs}\n📅 تاريخ الانضمام: {join_date}\n🔑 حالة كود الإحالة: {status}",
    'refresh_success': "✅ تم تحديث البيانات بنجاح",
    'error': "❌ حدث خطأ، يرجى المحاولة لاحقاً",
    'referral_bonus': "🎊 إحالة جديدة!\n+0.10$ تمت إضافتها إلى رصيدك",
    'referral_welcome': "👋 لقد انضممت عبر رابط {name}\n💰 لقد ربحوا 0.10$ من إحالتك"
}

# Database setup
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
        card_number TEXT,
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
    return "مستخدم غير معروف"

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
        markup.add(types.InlineKeyboardButton(f"انضم إلى {channel}", url=f"https://t.me/{channel.strip('@')}"))
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
                           TEXTS['not_subscribed'],
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
        bot.answer_callback_query(call.id, "❗ لم تنضم لجميع القنوات بعد", show_alert=True)

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
    bot.send_message(
        message.chat.id,
        TEXTS['enter_card'],
        reply_markup=payment_methods_markup()  # Keep payment methods visible
    )
    bot.register_next_step_handler(message, lambda m: process_payment(m, method))

def process_payment(message, method):
    try:
        user_id = message.from_user.id
        card_number = message.text.strip()
        
        # Check if user pressed a button instead of sending card number
        if message.text in TEXTS['payment_methods'] or message.text == TEXTS['back_menu']:
            show_main_menu(message)
            return
        
        if not card_number.isdigit() or len(card_number) < 8:
            bot.send_message(message.chat.id, TEXTS['invalid_card'], reply_markup=payment_methods_markup())
            return
        
        # Register payment request
        c.execute("INSERT INTO payment_requests (user_id, card_number, amount, payment_method) VALUES (?, ?, ?, ?)",
                 (user_id, card_number, 2.0, method))
        
        # Send approval request to admin
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ الموافقة", callback_data=f"approve_{user_id}"),
            types.InlineKeyboardButton("❌ الرفض", callback_data=f"reject_{user_id}")
        )
        
        admin_msg = (f"📌 طلب شراء كود جديد:\n\n"
                    f"👤 المستخدم: {get_user_info(user_id)}\n"
                    f"💳 الطريقة: {method}\n"
                    f"🔢 رقم الكرت: {card_number}\n"
                    f"🆔 كود المستخدم: {generate_code(user_id)}")
        
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
            
            bot.answer_callback_query(call.id, "تمت الموافقة على الطلب")
        else:
            # Reject request
            try:
                bot.send_message(user_id,
                              TEXTS['payment_rejected'],
                              reply_markup=main_menu_markup())
            except Exception as e:
                logging.error(f"Message sending failed: {e}")
            
            bot.answer_callback_query(call.id, "تم رفض الطلب")
        
        # Update request status
        c.execute("UPDATE payment_requests SET status = ? WHERE user_id = ? AND status = 'pending'",
                 (action + 'd', user_id))
        conn.commit()
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        logging.error(f"Admin decision error: {e}")

# [Rest of the handlers remain the same as previous versions, just using Arabic texts]

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
        print("🚀 البوت يعمل...")
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g')
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:
        logging.error(f"خطأ رئيسي: {e}")
