import telebot
from flask import Flask, request

API_TOKEN = '7759650411:AAH95VUJun0ZtueNRCFsFWRRiXnBk5h8lAs'
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Handle /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Welcome! Are you a Boy or a Girl?\nPlease type: Boy / Girl")

# Handle text
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    if message.text.lower() == "boy":
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.row("Unlock 1-week chat - $10")
        markup.row("Chat with 3 girls - $2")
        bot.send_message(message.chat.id, "Choose an offer:", reply_markup=markup)
    elif message.text.lower() == "girl":
        bot.send_message(message.chat.id, "Thanks! You’ll earn $0.1 per chat. When you reach $2, contact admin.")
    elif "unlock" in message.text.lower() or "chat with 3" in message.text.lower():
        bot.send_message(message.chat.id, "Send your Zain or Asiacell card number for access. We'll verify soon.")

# Flask Webhook
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
        return "ok"
    return "Bot is running."

# Set webhook on launch
import os
WEBHOOK_URL = f"https://grhdate.onrender.com/"
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)

# Run Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
