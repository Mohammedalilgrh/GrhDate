from flask import Flask, request
from threading import Thread
import telebot
from telebot import types
import sqlite3
import time
import logging
from datetime import datetime

app = Flask(__name__)
TOKEN = '7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g'
CHANNELS = ["@intearnn", "@s111sgrh"]
ORDER_CHANNEL = "@intorders"
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"
bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)

# تحسينات قاعدة البيانات
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
        investment_link TEXT,
        joined_date DATETIME DEFAULT CURRENT_TIMESTAMP
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
    ''')
    
    conn.commit()
    return conn, c

conn, c = init_db()

# الدوال المحسنة
def generate_code(user_id):
    return f"REF{user_id}"

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

def verify_code_ownership(user_id, code):
    c.execute("SELECT user_id FROM users WHERE code = ?", (code,))
    result = c.fetchone()
    return result and result[0] == user_id

# لوحات المفاتيح
def main_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💳 شراء كود الإحالة", "💰 سحب الأرباح")
    markup.row("📊 إحصائياتي", "🔗 مشاركة الرابط")
    markup.row("🔄 تحديث البيانات")
    return markup

def remove_keyboard():
    return types.ReplyKeyboardRemove()

def payment_methods_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💳 أسيا سيل", "💳 زين العراق")
    markup.row("🔙 القائمة الرئيسية")
    return markup

# المعالجات الرئيسية
@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        user_id = message.from_user.id
        if not check_subscription(user_id):
            show_subscription_alert(message)
            return

        args = message.text.split()
        referral_code = args[1] if len(args) > 1 else None
        
        # تسجيل/تحديث المستخدم
        code = generate_code(user_id)
        c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, code) VALUES (?, ?, ?, ?)",
                 (user_id, message.from_user.username, message.from_user.first_name, code))
        c.execute("UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                 (message.from_user.username, message.from_user.first_name, user_id))
        
        # معالجة الإحالة إذا كانت صالحة
        if referral_code and len(referral_code) > 3:
            handle_referral(user_id, referral_code)
        
        conn.commit()
        show_main_menu(message)
    except Exception as e:
        logging.error(f"خطأ في أمر البدء: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ، يرجى المحاولة لاحقاً", reply_markup=remove_keyboard())

def handle_referral(user_id, referral_code):
    try:
        # التحقق من صحة كود الإحالة
        c.execute("SELECT user_id, has_purchased FROM users WHERE code = ?", (referral_code,))
        result = c.fetchone()
        
        if result and result[1] == 1:  # إذا كان المحيل قد اشترى الكود
            referrer_id = result[0]
            
            # منع الإحالة الذاتية
            if referrer_id != user_id:
                # تسجيل الإحالة
                c.execute("INSERT OR IGNORE INTO referral_logs (referrer_id, referred_id) VALUES (?, ?)", 
                          (referrer_id, user_id))
                
                # منح المكافأة
                c.execute("UPDATE users SET balance = balance + 0.1, referrals = referrals + 1 WHERE user_id = ?", 
                          (referrer_id,))
                conn.commit()
                
                # إعلام المحيل
                try:
                    bot.send_message(referrer_id, 
                                    f"🎉 حصلت على 0.1$ لإحالة جديدة!\n\n"
                                    f"👤 المستخدم: {get_user_info(user_id)}\n"
                                    f"💰 رصيدك الحالي: {get_user_balance(referrer_id):.2f}$")
                except Exception as e:
                    logging.error(f"فشل إرسال إشعار الإحالة: {e}")
    except Exception as e:
        logging.error(f"خطأ في معالجة الإحالة: {e}")

@bot.message_handler(func=lambda message: message.text == "💳 شراء كود الإحالة")
def handle_purchase_request(message):
    user_id = message.from_user.id
    c.execute("SELECT has_purchased FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if result and result[0] == 1:
        bot.send_message(message.chat.id, 
                        "✅ لديك بالفعل كود إحالة نشط\n\n"
                        "🔗 يمكنك مشاركة الرابط من خلال زر '🔗 مشاركة الرابط'",
                        reply_markup=main_menu_markup())
        return
    
    bot.send_message(message.chat.id,
                    "💳 لشراء كود الإحالة الخاص بك:\n\n"
                    "سعر الكود: 2$\n"
                    "يمنحك الحق في:\n"
                    "- الحصول على 0.1$ لكل إحالة جديدة\n"
                    "- مشاركة رابطك الخاص\n\n"
                    "اختر طريقة الدفع:",
                    reply_markup=payment_methods_markup())

@bot.message_handler(func=lambda message: message.text in ["💳 أسيا سيل", "💳 زين العراق"])
def handle_payment_method(message):
    method = "asiacell" if "أسيا" in message.text else "zain"
    msg = bot.send_message(message.chat.id,
                          f"🔔 طريقة الدفع: {message.text}\n\n"
                          "📌 أرسل رقم الرصيد الآن:\n"
                          "(يجب أن يكون الرصيد 2$ على الأقل)",
                          reply_markup=remove_keyboard())
    bot.register_next_step_handler(msg, lambda m: process_payment(m, method))

def process_payment(message, method):
    try:
        user_id = message.from_user.id
        phone = message.text.strip()
        
        if not phone.isdigit() or len(phone) < 8:
            bot.send_message(message.chat.id, "❌ رقم غير صالح، يرجى المحاولة مرة أخرى", reply_markup=main_menu_markup())
            return
        
        # تسجيل طلب الدفع
        c.execute("INSERT INTO payment_requests (user_id, phone_number, amount, payment_method) VALUES (?, ?, ?, ?)",
                 (user_id, phone, 2.0, method))
        
        # إرسال طلب الموافقة للمسؤول
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_{user_id}"),
            types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
        )
        
        admin_msg = (f"📌 طلب شراء كود إحالة:\n\n"
                    f"👤 المستخدم: {get_user_info(user_id)}\n"
                    f"📱 الرقم: {phone}\n"
                    f"💳 الطريقة: {'أسيا سيل' if method == 'asiacell' else 'زين العراق'}\n"
                    f"🆔 كود المستخدم: {generate_code(user_id)}")
        
        bot.send_message(ORDER_CHANNEL, admin_msg, reply_markup=markup)
        bot.send_message(user_id, "📬 تم استلام طلبك، جاري المراجعة...", reply_markup=main_menu_markup())
        conn.commit()
    except Exception as e:
        logging.error(f"خطأ في معالجة الدفع: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ، يرجى المحاولة لاحقاً", reply_markup=main_menu_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_admin_decision(call):
    try:
        action, user_id = call.data.split("_")
        user_id = int(user_id)
        
        if action == "approve":
            # تفعيل كود الإحالة للمستخدم
            c.execute("UPDATE users SET has_purchased = 1 WHERE user_id = ?", (user_id,))
            
            # إعلام المستخدم
            try:
                code = generate_code(user_id)
                referral_link = f"https://t.me/{bot.get_me().username}?start={code}"
                bot.send_message(user_id,
                                f"🎉 تم تفعيل كود الإحالة الخاص بك!\n\n"
                                f"🔗 رابط الإحالة:\n{referral_link}\n\n"
                                f"💰 ستحصل على 0.1$ لكل شخص يسجل عبر رابطك",
                                reply_markup=main_menu_markup())
            except Exception as e:
                logging.error(f"فشل إرسال الرسالة: {e}")
            
            bot.answer_callback_query(call.id, "تم الموافقة على الطلب")
        else:
            # رفض الطلب
            try:
                bot.send_message(user_id,
                               "❌ تم رفض طلبك، يرجى التحقق من المعلومات والمحاولة لاحقاً",
                               reply_markup=main_menu_markup())
            except Exception as e:
                logging.error(f"فشل إرسال الرسالة: {e}")
            
            bot.answer_callback_query(call.id, "تم رفض الطلب")
        
        # تحديث حالة الطلب
        c.execute("UPDATE payment_requests SET status = ? WHERE user_id = ? AND status = 'pending'",
                 (action + 'd', user_id))
        conn.commit()
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        logging.error(f"خطأ في قرار المسؤول: {e}")

@bot.message_handler(func=lambda message: message.text == "🔗 مشاركة الرابط")
def handle_share_referral(message):
    user_id = message.from_user.id
    c.execute("SELECT has_purchased, code FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if not result or result[0] != 1:
        bot.send_message(message.chat.id,
                        "⚠️ يجب عليك شراء كود الإحالة أولاً\n\n"
                        "استخدم زر '💳 شراء كود الإحالة' لشراء الكود الخاص بك",
                        reply_markup=main_menu_markup())
        return
    
    referral_code = result[1]
    referral_link = f"https://t.me/{bot.get_me().username}?start={referral_code}"
    
    bot.send_message(message.chat.id,
                    f"🔗 رابط الإحالة الخاص بك:\n\n{referral_link}\n\n"
                    "📌 شارك هذا الرابط مع أصدقائك لربح 0.1$ لكل إحالة جديدة\n\n"
                    "⚡ سيحصل كل شخص يسجل عبر رابطك على:\n"
                    "- 0.1$ لك عند التسجيل\n"
                    "- فرصة لشراء كود إحالة خاص به",
                    reply_markup=main_menu_markup())

# ... (بقية الدوال مثل السحب والإحصائيات بنفس الطريقة مع التأكد من التحقق من has_purchased)

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
    bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g')
    return "Webhook is set!", 200

if __name__ == '__main__':
    print("Bot is running...")
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g')
    app.run(host="0.0.0.0", port=5000)
