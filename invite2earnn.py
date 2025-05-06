from flask import Flask, request
from threading import Thread
import telebot
from telebot import types
import sqlite3
import time
import logging
from datetime import datetime

# تهيئة التطبيق
app = Flask(__name__)
TOKEN = '7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g'
CHANNELS = ["@intearnn", "@s111sgrh"]  # قنوات الاشتراك الإجباري
ORDER_CHANNEL = "@intorders"
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"  # أضف أي دي الأدمن هنا
bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)

# إعداد قاعدة البيانات المحسنة
def init_db():
    conn = sqlite3.connect("data.db", check_same_thread=False)
    c = conn.cursor()
    
    # جدول المستخدمين مع تحسينات
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        code TEXT UNIQUE,
        balance REAL DEFAULT 0.0,
        referrals INTEGER DEFAULT 0,
        has_purchased BOOLEAN DEFAULT 0,
        investment_link TEXT,
        joined_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_active DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول الإحالات مع تحسينات التتبع
    c.execute('''CREATE TABLE IF NOT EXISTS referral_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER UNIQUE,
        reward_claimed BOOLEAN DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(referrer_id) REFERENCES users(user_id),
        FOREIGN KEY(referred_id) REFERENCES users(user_id)
    )''')
    
    # جدول المدفوعات مع تحسينات التتبع
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
    
    # جدول طلبات السحب مع تحسينات التتبع
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

# الدوال المساعدة المحسنة
def generate_code(user_id):
    return f"REF_{user_id}_{int(time.time())}"

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

def update_user_activity(user_id):
    c.execute("UPDATE users SET last_active = ? WHERE user_id = ?", 
             (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

# لوحات المفاتيح المحسنة
def main_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("💳 شراء كود الإحالة", "💰 سحب الأرباح")
    markup.row("📊 إحصائياتي", "🔗 مشاركة الرابط")
    markup.row("🔄 تحديث البيانات")
    return markup

def payment_methods_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("💳 أسيا سيل", "💳 زين العراق")
    markup.row("🔙 القائمة الرئيسية")
    return markup

def withdraw_methods_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("💳 زين العراق", "💳 أسيا سيل")
    markup.row("💳 ماستر كارد/كي كارد", "💳 عملة رقمية")
    markup.row("🔙 القائمة الرئيسية")
    return markup

# معالجات الأوامر المحسنة
@bot.message_handler(commands=['start', 'restart'])
def start_command(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "None"
        full_name = message.from_user.first_name
        if message.from_user.last_name:
            full_name += " " + message.from_user.last_name

        # التحقق من الاشتراك
        if not check_subscription(user_id):
            show_subscription_alert(message)
            return

        # إنشاء كود فريد للمستخدم
        code = generate_code(user_id)
        
        # تسجيل/تحديث بيانات المستخدم
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
        
        # معالجة الإحالة إذا وجدت
        args = message.text.split()
        if len(args) > 1:
            referral_code = args[1]
            handle_referral(user_id, referral_code)
        
        conn.commit()
        show_main_menu(message)
        update_user_activity(user_id)
        
    except Exception as e:
        logging.error(f"خطأ في أمر البدء: {e}")
        bot.send_message(message.chat.id, 
                        "❌ حدث خطأ، يرجى المحاولة لاحقاً",
                        reply_markup=types.ReplyKeyboardRemove())

def handle_referral(user_id, referral_code):
    try:
        # التحقق من صحة كود الإحالة
        c.execute("""
            SELECT user_id FROM users 
            WHERE code = ? AND has_purchased = 1
            """, (referral_code,))
        result = c.fetchone()
        
        if result and result[0] != user_id:  # منع الإحالة الذاتية
            referrer_id = result[0]
            
            # تسجيل الإحالة (تجاهل إذا كانت موجودة مسبقاً)
            c.execute("""
                INSERT OR IGNORE INTO referral_logs 
                (referrer_id, referred_id) VALUES (?, ?)
                """, (referrer_id, user_id))
            
            # تحديث إحصائيات المحيل
            c.execute("""
                UPDATE users SET 
                balance = balance + 0.1,
                referrals = referrals + 1 
                WHERE user_id = ?
                """, (referrer_id,))
            
            conn.commit()
            
            # إعلام المحيل
            try:
                bot.send_message(
                    referrer_id,
                    f"🎉 حصلت على 0.1$ لإحالة جديدة!\n\n"
                    f"👤 المستخدم: {get_user_info(user_id)}\n"
                    f"💰 رصيدك الحالي: {get_user_balance(referrer_id):.2f}$",
                    reply_markup=main_menu_markup()
                )
            except Exception as e:
                logging.error(f"فشل إرسال إشعار الإحالة: {e}")
                
    except Exception as e:
        logging.error(f"خطأ في معالجة الإحالة: {e}")

@bot.message_handler(func=lambda msg: msg.text == "💳 شراء كود الإحالة")
def handle_purchase_request(message):
    try:
        user_id = message.from_user.id
        c.execute("SELECT has_purchased FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        if result and result[0] == 1:
            bot.send_message(
                message.chat.id,
                "✅ لديك بالفعل كود إحالة نشط\n\n"
                "🔗 يمكنك مشاركة الرابط من خلال زر '🔗 مشاركة الرابط'",
                reply_markup=main_menu_markup()
            )
            return
        
        bot.send_message(
            message.chat.id,
            "💳 لشراء كود الإحالة الخاص بك:\n\n"
            "سعر الكود: 2$\n"
            "يمنحك الحق في:\n"
            "- الحصول على 0.1$ لكل إحالة جديدة\n"
            "- مشاركة رابطك الخاص\n\n"
            "اختر طريقة الدفع:",
            reply_markup=payment_methods_markup()
        )
        update_user_activity(user_id)
        
    except Exception as e:
        logging.error(f"خطأ في طلب الشراء: {e}")
        bot.send_message(
            message.chat.id,
            "❌ حدث خطأ، يرجى المحاولة لاحقاً",
            reply_markup=main_menu_markup()
        )

# ... (يتبع باقي المعالجات بنفس النمط المحسن)

# تشغيل البوت
if __name__ == '__main__':
    try:
        print("🚀 البوت يعمل...")
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g')
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:
        logging.error(f"خطأ رئيسي: {e}")
