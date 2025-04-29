from flask import Flask, request
import sqlite3
import requests
import time

app = Flask(__name__)

TOKEN = "7759650411:AAH95VUJun0ZtueNRCFsFWRRiXnBk5h8lAs"
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"
CHANNEL_USERNAME = "@grhdate"

def send_message(chat_id, text, buttons=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if buttons:
        payload["reply_markup"] = buttons
    requests.post(f"{BOT_URL}/sendMessage", json=payload)

def init_db():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            gender TEXT,
            age INTEGER,
            balance REAL DEFAULT 0,
            referral TEXT,
            is_girl INTEGER DEFAULT 0,
            matched_girls TEXT DEFAULT ""
        )
    """)
    conn.commit()
    conn.close()

@app.route("/", methods=["GET"])
def home():
    return "Bot is running."

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        username = message["from"].get("username", "")
        text = message.get("text", "")

        conn = sqlite3.connect("db.sqlite3")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()

        if text.lower() == "/start":
            send_message(chat_id, "Welcome! Are you a Boy or a Girl?

Please type: Boy / Girl")
        elif text.lower() in ["boy", "girl"]:
            c.execute("UPDATE users SET gender = ? WHERE user_id = ?", (text.lower(), user_id))
            conn.commit()
            if text.lower() == "girl":
                c.execute("UPDATE users SET is_girl = 1 WHERE user_id = ?", (user_id,))
                conn.commit()
                send_message(chat_id, "Thanks for joining! You'll earn $0.1 for each chat you join. Once you reach $2, message me for a payout.")
            else:
                buttons = {
                    "keyboard": [["Unlock 1-week chat - $10"], ["Chat with 3 girls - $2"]],
                    "resize_keyboard": True,
                    "one_time_keyboard": True
                }
                send_message(chat_id, "Choose an offer:", buttons)
        elif "unlock" in text.lower() or "chat with 3" in text.lower():
            send_message(chat_id, "To activate, send your Zain or Asiacell card number here. We'll verify and give you access.")
            requests.post(f"{BOT_URL}/sendMessage", json={
                "chat_id": CHANNEL_USERNAME,
                "text": f"New payment request from @{username} ({user_id}):
{text}"
            })

        conn.close()

    return "ok"
