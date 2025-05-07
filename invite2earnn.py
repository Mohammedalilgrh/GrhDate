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
CHANNELS = ["@intearnn", "@s111sgrh"]  # القنوات المطلوبة
ORDER_CHANNEL = "@intorders"
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"  # أضف أي دي الأدمن هنا
bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)

# النصوص العربية
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

# الدوال المساعدة
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

def get_user_balance(user_id):
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else 0.0

# لوحات المفاتيح
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

# معالجات الأوامر
@bot.message_handler(commands=['start', 'restart'])
def start_command(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "None"
        full_name = message.from_user.first_name or ""
        if message.from_user.last_name:
            full_name += f" {message.from_user.last_name}"

        # التحقق من الاشتراك
        if not check_subscription(user_id):
            show_subscription_alert(message)
            return

        # تسجيل/تحديث المستخدم
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
        logging.error(f"خطأ في أمر البدء: {e}")
        bot.send_message(message.chat.id, 
                        TEXTS['error'],
                        reply_markup=types.ReplyKeyboardRemove())

def show_subscription_alert(message):
    markup = types.InlineKeyboardMarkup()
    for channel in CHANNELS:
        markup.add(types.InlineKeyboardButton(f"اشترك في {channel}", url=f"https://t.me/{channel.strip('@')}"))
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
        logging.error(f"خطأ في طلب الشراء: {e}")
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
        
        # تسجيل طلب الدفع
        c.execute("INSERT INTO payment_requests (user_id, phone_number, amount, payment_method) VALUES (?, ?, ?, ?)",
                 (user_id, phone, 2.0, method))
        
        # إرسال طلب الموافقة للمسؤول
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_{user_id}"),
            types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
        )
        
        admin_msg = (f"📌 طلب شراء كود إحالة جديد:\n\n"
                    f"👤 المستخدم: {get_user_info(user_id)}\n"
                    f"📱 الرقم: {phone}\n"
                    f"💳 الطريقة: {message.text}\n"
                    f"🆔 كود المستخدم: {generate_code(user_id)}")
        
        bot.send_message(ORDER_CHANNEL, admin_msg, reply_markup=markup)
        bot.send_message(user_id, TEXTS['payment_request_sent'], reply_markup=main_menu_markup())
        conn.commit()
    except Exception as e:
        logging.error(f"خطأ في معالجة الدفع: {e}")
        bot.send_message(message.chat.id, TEXTS['error'], reply_markup=main_menu_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_admin_decision(call):
    try:
        action, user_id = call.data.split("_")
        user_id = int(user_id)
        
        if action == "approve":
            # تفعيل كود الإحالة للمستخدم
            c.execute("UPDATE users SET has_purchased = 1 WHERE user_id = ?", (user_id,))
            
            # إنشاء رابط الإحالة
            code = generate_code(user_id)
            referral_link = f"https://t.me/{bot.get_me().username}?start={code}"
            
            # إعلام المستخدم
            try:
                bot.send_message(user_id,
                                TEXTS['payment_approved'].format(link=referral_link),
                                reply_markup=main_menu_markup())
            except Exception as e:
                logging.error(f"فشل إرسال الرسالة: {e}")
            
            bot.answer_callback_query(call.id, "تم قبول الطلب")
        else:
            # رفض الطلب
            try:
                bot.send_message(user_id,
                               TEXTS['payment_rejected'],
                               reply_markup=main_menu_markup())
            except Exception as e:
                logging.error(f"فشل إرسال الرسالة: {e}")
            
            bot.answer_callback_query(call.id, "تم رفض الطلب")
        
        # تحديث حالة الطلب
        c.execute("UPDATE payment_requests SET status = ? WHERE user_id = ? AND status = 'pending'",
                 ('approved' if action == 'approve' else 'rejected', user_id))
        conn.commit()
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        logging.error(f"خطأ في قرار المسؤول: {e}")

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
        logging.error(f"خطأ في طلب السحب: {e}")
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
        logging.error(f"خطأ في التحقق من كود السحب: {e}")
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
        logging.error(f"خطأ في اختيار طريقة السحب: {e}")
        bot.send_message(message.chat.id,
                        TEXTS['error'],
                        reply_markup=main_menu_markup())

def process_withdraw(message, method):
    try:
        user_id = message.from_user.id
        account_info = message.text.strip()
        balance = get_user_balance(user_id)
        
        # التحقق من صحة المعلومات حسب طريقة السحب
        if method in ["zain", "asiacell"] and not account_info.isdigit():
            bot.send_message(message.chat.id,
                           TEXTS['invalid_phone'],
                           reply_markup=main_menu_markup())
            return
        
        # تسجيل طلب السحب
        c.execute("INSERT INTO withdrawal_requests (user_id, amount, method, account_info) VALUES (?, ?, ?, ?)",
                 (user_id, balance, method, account_info))
        
        # خصم المبلغ من رصيد المستخدم
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?",
                 (balance, user_id))
        
        # إرسال إشعار للمسؤول
        admin_msg = (f"📌 طلب سحب جديد:\n\n"
                    f"👤 المستخدم: {get_user_info(user_id)}\n"
                    f"💵 المبلغ: {balance:.2f}$\n"
                    f"💳 الطريقة: {method}\n"
                    f"📝 المعلومات: {account_info}")
        
        bot.send_message(ORDER_CHANNEL, admin_msg)
        
        # إعلام المستخدم
        bot.send_message(message.chat.id,
                       TEXTS['withdraw_request_sent'],
                       reply_markup=main_menu_markup())
        
        conn.commit()
        
    except Exception as e:
        logging.error(f"خطأ في معالجة السحب: {e}")
        bot.send_message(message.chat.id,
                        TEXTS['error'],
                        reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == TEXTS['main_menu'][2])
def handle_user_stats(message):
    try:
        user_id = message.from_user.id
        
        # الحصول على بيانات المستخدم
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
        
        # حساب إجمالي الإحالات
        c.execute("SELECT COUNT(*) FROM referral_logs WHERE referrer_id = ?", (user_id,))
        total_refs = c.fetchone()[0]
        
        status = "✅ مفعل" if has_purchased else "❌ غير مفعل"
        
        # إعداد رسالة الإحصائيات
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
        logging.error(f"خطأ في عرض الإحصائيات: {e}")
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
        logging.error(f"خطأ في تحديث البيانات: {e}")
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
        
        # الحصول على بيانات المستخدم
        c.execute("SELECT balance, referrals FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        if not result:
            bot.send_message(message.chat.id,
                           TEXTS['error'],
                           reply_markup=types.ReplyKeyboardRemove())
            return
            
        balance, referrals = result
        
        # إعداد رسالة الترحيب
        welcome_msg = TEXTS['start'].format(
            name=get_user_info(user_id),
            balance=balance,
            refs=referrals
        )
        
        bot.send_message(message.chat.id,
                       welcome_msg,
                       reply_markup=main_menu_markup())
        
    except Exception as e:
        logging.error(f"خطأ في عرض القائمة الرئيسية: {e}")
        bot.send_message(message.chat.id,
                        TEXTS['error'],
                        reply_markup=types.ReplyKeyboardRemove())

# مسارات Flask
@app.route('/' + TOKEN, methods=['POST'])
def bot_webhook():
    try:
        json_data = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        logging.error(f"خطأ في webhook: {e}")
        return "Error", 500

@app.route('/')
def set_webhook():
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g')
        return "تم إعداد Webhook بنجاح!", 200
    except Exception as e:
        logging.error(f"خطأ في إعداد webhook: {e}")
        return "فشل إعداد Webhook", 500

if __name__ == '__main__':
    try:
        print("🚀 البوت يعمل الآن...")
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g')
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:
        logging.error(f"خطأ رئيسي: {e}")
