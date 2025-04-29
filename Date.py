import telebot from flask import Flask, request import sqlite3 import os import time import threading

Telegram bot token and settings

API_TOKEN = '7759650411:AAH95VUJun0ZtueNRCFsFWRRiXnBk5h8lAs' bot = telebot.TeleBot(API_TOKEN) app = Flask(name)

ADMIN_CHANNEL = '@grhdate' MATCH_DURATION = 900  # 15 minutes in seconds

Initialize SQLite DB

def init_db(): conn = sqlite3.connect('db.sqlite3') c = conn.cursor() c.execute(''' CREATE TABLE IF NOT EXISTS users ( user_id INTEGER PRIMARY KEY, username TEXT, gender TEXT, age INTEGER, referral TEXT, balance INTEGER DEFAULT 0, chats_left INTEGER DEFAULT 0, active_chat_with INTEGER DEFAULT 0, last_matched INTEGER DEFAULT 0 ) ''') conn.commit() conn.close()

init_db()

Welcome and gender input

@bot.message_handler(commands=['start']) def start_message(message): user_id = message.from_user.id username = message.from_user.username or "" conn = sqlite3.connect('db.sqlite3') c = conn.cursor() c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username)) conn.commit() conn.close() bot.send_message(user_id, "Welcome! Are you a Boy or a Girl?\nPlease type: Boy / Girl")

@bot.message_handler(func=lambda m: m.text.lower() in ['boy', 'girl']) def set_gender(message): user_id = message.from_user.id gender = message.text.lower() conn = sqlite3.connect('db.sqlite3') c = conn.cursor() c.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id)) conn.commit() conn.close()

if gender == 'girl':
    bot.send_message(user_id, "Thanks! You’ll be matched anonymously with boys. Sit tight.")
else:
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row("Unlock 1-week chat - $10")
    markup.row("Chat with 3 girls - $2")
    bot.send_message(user_id, "Choose an offer:", reply_markup=markup)

@bot.message_handler(func=lambda m: 'unlock' in m.text.lower() or 'chat with 3' in m.text.lower()) def request_payment(message): user_id = message.from_user.id username = message.from_user.username or "NoUsername" bot.send_message(user_id, "Send your Zain or Asiacell card number. We'll verify and activate access.") bot.send_message(ADMIN_CHANNEL, f"Payment request from @{username} ({user_id}):\n{message.text}")

@bot.message_handler(func=lambda m: m.text.lower().startswith('card ')) def handle_card_submission(message): user_id = message.from_user.id card = message.text[5:].strip() username = message.from_user.username or "NoUsername" bot.send_message(ADMIN_CHANNEL, f"Card received from @{username} ({user_id}): {card}\nReply /accept_{user_id} or /reject_{user_id}")

@bot.message_handler(commands=['accept_']) def accept_user(message): user_id = int(message.text.split('_')[1]) conn = sqlite3.connect('db.sqlite3') c = conn.cursor() c.execute("UPDATE users SET chats_left = 3 WHERE user_id = ?", (user_id,)) conn.commit() conn.close() bot.send_message(user_id, "Access granted. You can now chat with 3 girls anonymously. Reply /match to start.")

@bot.message_handler(commands=['reject_']) def reject_user(message): user_id = int(message.text.split('_')[1]) bot.send_message(user_id, "Your payment was rejected. Please send a valid card number.")

@bot.message_handler(commands=['match']) def match_users(message): user_id = message.from_user.id conn = sqlite3.connect('db.sqlite3') c = conn.cursor() c.execute("SELECT gender, chats_left FROM users WHERE user_id = ?", (user_id,)) result = c.fetchone() if not result: bot.send_message(user_id, "You must register first. Type /start") return

gender, chats_left = result
if gender != 'boy':
    bot.send_message(user_id, "Only boys can initiate match requests.")
    return
if chats_left <= 0:
    bot.send_message(user_id, "No remaining chats. Use the buttons to buy more.")
    return

c.execute("SELECT user_id FROM users WHERE gender = 'girl' AND active_chat_with = 0 LIMIT 1")
girl = c.fetchone()
if not girl:
    bot.send_message(user_id, "No girls available right now. Try again later.")
    return

girl_id = girl[0]
now = int(time.time())
c.execute("UPDATE users SET active_chat_with = ?, last_matched = ? WHERE user_id = ?", (girl_id, now, user_id))
c.execute("UPDATE users SET active_chat_with = ?, last_matched = ? WHERE user_id = ?", (user_id, now, girl_id))
c.execute("UPDATE users SET chats_left = chats_left - 1 WHERE user_id = ?", (user_id,))
conn.commit()
conn.close()

bot.send_message(user_id, "You've been matched anonymously. You have 15 minutes to chat. Say hi!")
bot.send_message(girl_id, "You've been matched anonymously with a boy. You have 15 minutes to chat. Say hi!")

# Timer to auto-end chat
threading.Thread(target=end_chat_after, args=(user_id, girl_id, now)).start()

def end_chat_after(user1, user2, match_time): time.sleep(MATCH_DURATION) conn = sqlite3.connect('db.sqlite3') c = conn.cursor() c.execute("SELECT last_matched FROM users WHERE user_id = ?", (user1,)) user1_time = c.fetchone()[0] if user1_time == match_time: c.execute("UPDATE users SET active_chat_with = 0 WHERE user_id IN (?, ?)", (user1, user2)) conn.commit() bot.send_message(user1, "Your 15-minute match has ended.") bot.send_message(user2, "Your 15-minute match has ended.") conn.close()

@app.route('/', methods=['GET', 'POST']) def webhook(): if request.method == 'POST': bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))]) return "ok" return "Bot is running."

Set webhook

bot.remove_webhook() bot.set_webhook(url="https://grhdate.onrender.com/")

if name == "main": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

