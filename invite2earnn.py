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
        last_active DATETIME DEFAULT CURRENT_TIMESTAMP
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
def main_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("💳 Buy Referral Code", "💰 Withdraw Earnings")
    markup.row("📊 My Stats", "🔄 Refresh Data")
    return markup

def payment_methods_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("💳 AsiaCell", "💳 Zain Iraq")
    markup.row("🔙 Main Menu")
    return markup

def withdraw_methods_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.row("💳 Zain Iraq", "💳 AsiaCell")
    markup.row("💳 MasterCard/KNet", "💳 Crypto")
    markup.row("🔙 Main Menu")
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

        # Check subscription
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
                        "❌ Error occurred, please try later",
                        reply_markup=types.ReplyKeyboardRemove())

def show_subscription_alert(message):
    markup = types.InlineKeyboardMarkup()
    for channel in CHANNELS:
        markup.add(types.InlineKeyboardButton(f"Join {channel}", url=f"https://t.me/{channel.strip('@')}"))
    markup.add(types.InlineKeyboardButton("✅ Done", callback_data="check_sub"))
    bot.send_message(message.chat.id, "⚠️ To start, please join our channels:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_subscription_callback(call):
    if check_subscription(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "❗ You haven't joined all channels", show_alert=True)

@bot.message_handler(func=lambda message: message.text == "💳 Buy Referral Code")
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
                f"✅ You already have an active referral code\n\n"
                f"🔗 You can share this link:\n{referral_link}\n\n"
                f"💰 You'll earn 0.1$ per new referral",
                reply_markup=main_menu_markup()
            )
            return
        
        bot.send_message(
            message.chat.id,
            "💳 To buy your referral code:\n\n"
            "Code price: 2$\n"
            "Gives you the right to:\n"
            "- Earn 0.1$ per new referral\n"
            "- Share your unique link to earn more\n\n"
            "Choose payment method:",
            reply_markup=payment_methods_markup()
        )
        update_user_activity(user_id)
        
    except Exception as e:
        logging.error(f"Purchase request error: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Error occurred, please try later",
            reply_markup=main_menu_markup()
        )

@bot.message_handler(func=lambda message: message.text in ["💳 AsiaCell", "💳 Zain Iraq"])
def handle_payment_method(message):
    method = "asiacell" if "Asia" in message.text else "zain"
    msg = bot.send_message(message.chat.id,
                          f"🔔 Payment method: {message.text}\n\n"
                          "📌 Please send your phone number:\n"
                          "(Must have at least 2$ balance)",
                          reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, lambda m: process_payment(m, method))

def process_payment(message, method):
    try:
        user_id = message.from_user.id
        phone = message.text.strip()
        
        if not phone.isdigit() or len(phone) < 8:
            bot.send_message(message.chat.id, "❌ Invalid number, please try again", reply_markup=main_menu_markup())
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
        bot.send_message(user_id, "📬 Your request received, under review...", reply_markup=main_menu_markup())
        conn.commit()
    except Exception as e:
        logging.error(f"Payment processing error: {e}")
        bot.send_message(message.chat.id, "❌ Error occurred, please try later", reply_markup=main_menu_markup())

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
                                f"🎉 Your referral code activated!\n\n"
                                f"🔗 Referral link:\n{referral_link}\n\n"
                                f"💰 Earn 0.1$ for each signup via your link\n\n"
                                f"📌 Share this link to start earning",
                                reply_markup=main_menu_markup())
            except Exception as e:
                logging.error(f"Message sending failed: {e}")
            
            bot.answer_callback_query(call.id, "Request approved")
        else:
            # Reject request
            try:
                bot.send_message(user_id,
                               "❌ Your request was rejected, please check info and try later",
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

@bot.message_handler(func=lambda message: message.text == "💰 Withdraw Earnings")
def handle_withdraw_request(message):
    try:
        user_id = message.from_user.id
        balance = get_user_balance(user_id)
        
        if balance < 2.0:
            bot.send_message(message.chat.id,
                            "❗ Minimum withdrawal is 2$\n\n"
                            "You can increase your balance by:\n"
                            "- Getting more referrals\n"
                            "- Buying additional referral codes",
                            reply_markup=main_menu_markup())
            return
        
        msg = bot.send_message(message.chat.id,
                             "📤 To withdraw earnings:\n\n"
                             "Please send your referral code for verification:",
                             reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, verify_withdraw_code)
        
    except Exception as e:
        logging.error(f"Withdrawal request error: {e}")
        bot.send_message(message.chat.id,
                        "❌ Error occurred, please try later",
                        reply_markup=main_menu_markup())

def verify_withdraw_code(message):
    try:
        user_id = message.from_user.id
        user_code = generate_code(user_id)
        
        if message.text.strip() == user_code:
            bot.send_message(message.chat.id,
                           "💰 Choose withdrawal method:",
                           reply_markup=withdraw_methods_markup())
        else:
            bot.send_message(message.chat.id,
                           "❌ Verification code incorrect",
                           reply_markup=main_menu_markup())
            
    except Exception as e:
        logging.error(f"Withdrawal verification error: {e}")
        bot.send_message(message.chat.id,
                        "❌ Error occurred, please try later",
                        reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text in ["💳 Zain Iraq", "💳 AsiaCell", "💳 MasterCard/KNet", "💳 Crypto"])
def handle_withdraw_method(message):
    try:
        method = {
            "💳 Zain Iraq": "zain",
            "💳 AsiaCell": "asiacell",
            "💳 MasterCard/KNet": "card",
            "💳 Crypto": "crypto"
        }[message.text]
        
        msg = bot.send_message(message.chat.id,
                             f"📤 Please send your {message.text} details:",
                             reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, lambda m: process_withdraw(m, method))
        
    except Exception as e:
        logging.error(f"Withdrawal method error: {e}")
        bot.send_message(message.chat.id,
                        "❌ Error occurred, please try later",
                        reply_markup=main_menu_markup())

def process_withdraw(message, method):
    try:
        user_id = message.from_user.id
        account_info = message.text.strip()
        balance = get_user_balance(user_id)
        
        # Validate info based on method
        if method in ["zain", "asiacell"] and not account_info.isdigit():
            bot.send_message(message.chat.id,
                           "❌ Invalid account number for this method",
                           reply_markup=main_menu_markup())
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
                       f"✅ Withdrawal request received\n\n"
                       f"⏳ Processing within 24 hours\n"
                       f"📌 You'll be notified when completed",
                       reply_markup=main_menu_markup())
        
        conn.commit()
        
    except Exception as e:
        logging.error(f"Withdrawal processing error: {e}")
        bot.send_message(message.chat.id,
                        "❌ Error occurred, please try later",
                        reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == "📊 My Stats")
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
                           "❌ No data found",
                           reply_markup=main_menu_markup())
            return
            
        balance, referrals, has_purchased, join_date = result
        
        # Calculate total referrals
        c.execute("SELECT COUNT(*) FROM referral_logs WHERE referrer_id = ?", (user_id,))
        total_refs = c.fetchone()[0]
        
        # Prepare stats message
        stats_msg = (f"📊 Your stats:\n\n"
                    f"💰 Current balance: {balance:.2f}$\n"
                    f"👥 Active referrals: {referrals}\n"
                    f"🔗 Total referrals: {total_refs}\n"
                    f"📅 Join date: {join_date[:10]}\n"
                    f"🔑 Referral code: {'✅ Active' if has_purchased else '❌ Inactive'}")
        
        bot.send_message(message.chat.id,
                       stats_msg,
                       reply_markup=main_menu_markup())
        
    except Exception as e:
        logging.error(f"Stats display error: {e}")
        bot.send_message(message.chat.id,
                        "❌ Error occurred, please try later",
                        reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == "🔄 Refresh Data")
def handle_refresh(message):
    try:
        user_id = message.from_user.id
        update_user_activity(user_id)
        bot.send_message(message.chat.id,
                        "✅ Data refreshed successfully",
                        reply_markup=main_menu_markup())
    except Exception as e:
        logging.error(f"Refresh error: {e}")
        bot.send_message(message.chat.id,
                        "❌ Error occurred, please try later",
                        reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == "🔙 Main Menu")
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
                           "❌ No data found",
                           reply_markup=types.ReplyKeyboardRemove())
            return
            
        balance, referrals, has_purchased = result
        
        # Prepare welcome message
        welcome_msg = (f"Welcome {get_user_info(user_id)} 👋\n\n"
                      f"💰 Current balance: {balance:.2f}$\n"
                      f"👥 Referrals: {referrals}\n\n"
                      f"📌 Choose from menu:")
        
        bot.send_message(message.chat.id,
                       welcome_msg,
                       reply_markup=main_menu_markup())
        
    except Exception as e:
        logging.error(f"Main menu error: {e}")
        bot.send_message(message.chat.id,
                        "❌ Error occurred, please try later",
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
