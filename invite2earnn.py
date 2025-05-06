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

# لوحات المفاتيح المحسنة
def main_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("💳 شراء كود الإحالة", "💰 سحب الأرباح")
    markup.row("📊 إحصائياتي", "🔄 تحديث البيانات")
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

        # تسجيل/تحديث بيانات المستخدم
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
                        "❌ حدث خطأ، يرجى المحاولة لاحقاً",
                        reply_markup=types.ReplyKeyboardRemove())

def show_subscription_alert(message):
    markup = types.InlineKeyboardMarkup()
    for channel in CHANNELS:
        markup.add(types.InlineKeyboardButton(f"اشترك في {channel}", url=f"https://t.me/{channel.strip('@')}"))
    markup.add(types.InlineKeyboardButton("✅ تم الاشتراك", callback_data="check_sub"))
    bot.send_message(message.chat.id, "⚠️ للبدء، يجب الاشتراك في القنوات التالية:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_subscription_callback(call):
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "❗ لم تكمل الاشتراك في جميع القنوات", show_alert=True)

@bot.message_handler(func=lambda message: message.text == "💳 شراء كود الإحالة")
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
                f"✅ لديك بالفعل كود إحالة نشط\n\n"
                f"🔗 يمكنك مشاركة هذا الرابط:\n{referral_link}\n\n"
                f"💰 ستحصل على 0.1$ لكل إحالة جديدة",
                reply_markup=main_menu_markup()
            )
            return
        
        bot.send_message(
            message.chat.id,
            "💳 لشراء كود الإحالة الخاص بك:\n\n"
            "سعر الكود: 2$\n"
            "يمنحك الحق في:\n"
            "- الحصول على 0.1$ لكل إحالة جديدة\n"
            "- مشاركة رابطك الخاص لكسب المزيد\n\n"
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

@bot.message_handler(func=lambda message: message.text in ["💳 أسيا سيل", "💳 زين العراق"])
def handle_payment_method(message):
    method = "asiacell" if "أسيا" in message.text else "zain"
    msg = bot.send_message(message.chat.id,
                          f"🔔 طريقة الدفع: {message.text}\n\n"
                          "📌 أرسل رقم الرصيد الآن:\n"
                          "(يجب أن يكون الرصيد 2$ على الأقل)",
                          reply_markup=types.ReplyKeyboardRemove())
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
            
            # إنشاء رابط الإحالة
            code = generate_code(user_id)
            referral_link = f"https://t.me/{bot.get_me().username}?start={code}"
            
            # إعلام المستخدم
            try:
                bot.send_message(user_id,
                                f"🎉 تم تفعيل كود الإحالة الخاص بك!\n\n"
                                f"🔗 رابط الإحالة:\n{referral_link}\n\n"
                                f"💰 ستحصل على 0.1$ لكل شخص يسجل عبر رابطك\n\n"
                                f"📌 شارك هذا الرابط مع أصدقائك لبدء الكسب",
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

@bot.message_handler(func=lambda message: message.text == "💰 سحب الأرباح")
def handle_withdraw_request(message):
    try:
        user_id = message.from_user.id
        balance = get_user_balance(user_id)
        
        if balance < 2.0:
            bot.send_message(message.chat.id,
                            "❗ الحد الأدنى للسحب هو 2$\n\n"
                            "يمكنك زيادة رصيدك عن طريق:\n"
                            "- جذب المزيد من الإحالات\n"
                            "- شراء كود إحالة إضافي",
                            reply_markup=main_menu_markup())
            return
        
        msg = bot.send_message(message.chat.id,
                             "📤 لسحب الأرباح:\n\n"
                             "أرسل كود الإحالة الخاص بك للتأكيد:",
                             reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, verify_withdraw_code)
        
    except Exception as e:
        logging.error(f"خطأ في طلب السحب: {e}")
        bot.send_message(message.chat.id,
                        "❌ حدث خطأ، يرجى المحاولة لاحقاً",
                        reply_markup=main_menu_markup())

def verify_withdraw_code(message):
    try:
        user_id = message.from_user.id
        user_code = generate_code(user_id)
        
        if message.text.strip() == user_code:
            bot.send_message(message.chat.id,
                           "💰 اختر طريقة السحب:",
                           reply_markup=withdraw_methods_markup())
        else:
            bot.send_message(message.chat.id,
                           "❌ كود التأكيد غير صحيح",
                           reply_markup=main_menu_markup())
            
    except Exception as e:
        logging.error(f"خطأ في التحقق من كود السحب: {e}")
        bot.send_message(message.chat.id,
                        "❌ حدث خطأ، يرجى المحاولة لاحقاً",
                        reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text in ["💳 زين العراق", "💳 أسيا سيل", "💳 ماستر كارد/كي كارد", "💳 عملة رقمية"])
def handle_withdraw_method(message):
    try:
        method = {
            "💳 زين العراق": "zain",
            "💳 أسيا سيل": "asiacell",
            "💳 ماستر كارد/كي كارد": "card",
            "💳 عملة رقمية": "crypto"
        }[message.text]
        
        msg = bot.send_message(message.chat.id,
                             f"📤 أرسل معلومات {message.text} للسحب:",
                             reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, lambda m: process_withdraw(m, method))
        
    except Exception as e:
        logging.error(f"خطأ في اختيار طريقة السحب: {e}")
        bot.send_message(message.chat.id,
                        "❌ حدث خطأ، يرجى المحاولة لاحقاً",
                        reply_markup=main_menu_markup())

def process_withdraw(message, method):
    try:
        user_id = message.from_user.id
        account_info = message.text.strip()
        balance = get_user_balance(user_id)
        
        # التحقق من صحة المعلومات حسب طريقة السحب
        if method in ["zain", "asiacell"] and not account_info.isdigit():
            bot.send_message(message.chat.id,
                           "❌ رقم الحساب غير صالح لهذه الطريقة",
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
                       f"✅ تم استلام طلب السحب بنجاح\n\n"
                       f"⏳ جاري معالجة طلبك خلال 24 ساعة\n"
                       f"📌 سيتم إعلامك عند اكتمال العملية",
                       reply_markup=main_menu_markup())
        
        conn.commit()
        
    except Exception as e:
        logging.error(f"خطأ في معالجة السحب: {e}")
        bot.send_message(message.chat.id,
                        "❌ حدث خطأ، يرجى المحاولة لاحقاً",
                        reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == "📊 إحصائياتي")
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
                           "❌ لم يتم العثور على بياناتك",
                           reply_markup=main_menu_markup())
            return
            
        balance, referrals, has_purchased, join_date = result
        
        # حساب إجمالي الإحالات
        c.execute("SELECT COUNT(*) FROM referral_logs WHERE referrer_id = ?", (user_id,))
        total_refs = c.fetchone()[0]
        
        # إعداد رسالة الإحصائيات
        stats_msg = (f"📊 إحصائياتك الشخصية:\n\n"
                    f"💰 الرصيد الحالي: {balance:.2f}$\n"
                    f"👥 عدد الإحالات النشطة: {referrals}\n"
                    f"🔗 إجمالي الإحالات: {total_refs}\n"
                    f"📅 تاريخ الانضمام: {join_date[:10]}\n"
                    f"🔑 حالة كود الإحالة: {'✅ مفعل' if has_purchased else '❌ غير مفعل'}")
        
        bot.send_message(message.chat.id,
                       stats_msg,
                       reply_markup=main_menu_markup())
        
    except Exception as e:
        logging.error(f"خطأ في عرض الإحصائيات: {e}")
        bot.send_message(message.chat.id,
                        "❌ حدث خطأ، يرجى المحاولة لاحقاً",
                        reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == "🔄 تحديث البيانات")
def handle_refresh(message):
    try:
        user_id = message.from_user.id
        update_user_activity(user_id)
        bot.send_message(message.chat.id,
                        "✅ تم تحديث بياناتك بنجاح",
                        reply_markup=main_menu_markup())
    except Exception as e:
        logging.error(f"خطأ في تحديث البيانات: {e}")
        bot.send_message(message.chat.id,
                        "❌ حدث خطأ، يرجى المحاولة لاحقاً",
                        reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == "🔙 القائمة الرئيسية")
def handle_back_to_main(message):
    show_main_menu(message)

def show_main_menu(message):
    try:
        user_id = message.from_user.id
        update_user_activity(user_id)
        
        # الحصول على بيانات المستخدم
        c.execute("SELECT balance, referrals, has_purchased FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        if not result:
            bot.send_message(message.chat.id,
                           "❌ لم يتم العثور على بياناتك",
                           reply_markup=types.ReplyKeyboardRemove())
            return
            
        balance, referrals, has_purchased = result
        
        # إعداد رسالة الترحيب
        welcome_msg = (f"مرحباً {get_user_info(user_id)} 👋\n\n"
                      f"💰 رصيدك الحالي: {balance:.2f}$\n"
                      f"👥 عدد الإحالات: {referrals}\n\n"
                      f"📌 اختر أحد الخيارات من القائمة:")
        
        bot.send_message(message.chat.id,
                       welcome_msg,
                       reply_markup=main_menu_markup())
        
    except Exception as e:
        logging.error(f"خطأ في عرض القائمة الرئيسية: {e}")
        bot.send_message(message.chat.id,
                        "❌ حدث خطأ، يرجى المحاولة لاحقاً",
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
        bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g}')
        return "Webhook is set!", 200
    except Exception as e:
        logging.error(f"خطأ في إعداد webhook: {e}")
        return "خطأ في إعداد webhook", 500

if __name__ == '__main__':
    try:
        print("🚀 البوت يعمل...")
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f'https://invite2earnn.onrender.com/7897542906:AAFWO23YZhUhLpDJ500d6yZ4jcUnPZY450g}')
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:
        logging.error(f"خطأ رئيسي: {e}")
