import os
import logging
from datetime import datetime, timedelta
import threading
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
)

# ===== YOUR PERSONAL CONFIGURATION =====
BOT_TOKEN = "7759650411:AAH95VUJun0ZtueNRCFsFWRRiXnBk5h8lAs"
ORDERS_CHANNEL = "grhdate"  # Your private orders channel (without @)
WEBHOOK_URL = "https://grhdate.onrender.com"  # Your Render webhook URL
# =======================================

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Payment options
PAYMENT_OPTIONS = {
    "weekly": {"price": 10, "description": "Unlock chatting with girls for a week"},
    "three_chats": {"price": 2, "description": "Chat with 3 girls (15 min each)"},
}

# Conversation states
GENDER, AGE, MAIN_MENU, PAYMENT, CHATTING = range(5)

# User data storage
user_data = {}
active_chats = {}
pending_payments = {}

class User:
    def __init__(self, user_id: int, gender: str, age: int):
        self.user_id = user_id
        self.gender = gender
        self.age = age
        self.payment_status = "unpaid"
        self.chats_remaining = 0
        self.payment_expiry = None
        self.referrals = 0
        self.waiting_for_match = False
        self.current_chat = None

    def activate_weekly(self):
        self.payment_status = "paid"
        self.chats_remaining = float('inf')
        self.payment_expiry = datetime.now() + timedelta(days=7)
    
    def activate_three_chats(self):
        self.payment_status = "paid"
        self.chats_remaining = 3
        self.payment_expiry = datetime.now() + timedelta(days=30)
    
    def add_referral(self):
        self.referrals += 1
        if self.referrals % 1 == 0:
            self.chats_remaining += 1
    
    def can_chat(self):
        if self.payment_status != "paid":
            return False
        if self.payment_expiry and datetime.now() > self.payment_expiry:
            return False
        if self.chats_remaining == 0:
            return False
        return True
    
    def start_chat(self):
        if self.can_chat() and self.chats_remaining != float('inf'):
            self.chats_remaining -= 1

def start(update: Update, context: CallbackContext) -> int:
    """Start command with referral handling."""
    user_id = update.message.from_user.id
    
    # Check for referral link
    if context.args and context.args[0].startswith('ref'):
        try:
            referrer_id = int(context.args[0][3:])
            if referrer_id in user_data:
                user_data[referrer_id].add_referral()
                context.bot.send_message(
                    referrer_id,
                    "🎉 You got a new referral! You've earned 1 free chat."
                )
        except (IndexError, ValueError):
            pass
    
    if user_id in user_data:
        show_main_menu(update, context, user_id)
        return MAIN_MENU
    
    update.message.reply_text(
        "🔥 Secret Dating Chat 🔥\n\n"
        "Are you a Boy or Girl? Type:\n\n"
        "Boy / Girl"
    )
    return GENDER

def gender_received(update: Update, context: CallbackContext) -> int:
    gender = update.message.text.strip().lower()
    if gender not in ["boy", "girl"]:
        update.message.reply_text("Please type either 'Boy' or 'Girl'")
        return GENDER
    
    context.user_data['gender'] = gender
    update.message.reply_text("How old are you? (18-99):")
    return AGE

def age_received(update: Update, context: CallbackContext) -> int:
    try:
        age = int(update.message.text.strip())
        if age < 18 or age > 99:
            raise ValueError
    except ValueError:
        update.message.reply_text("Please enter a valid age between 18-99")
        return AGE
    
    user_id = update.message.from_user.id
    user_data[user_id] = User(user_id, context.user_data['gender'], age)
    
    show_main_menu(update, context, user_id)
    return MAIN_MENU

def show_main_menu(update: Update, context: CallbackContext, user_id: int):
    user = user_data[user_id]
    text = "🌟 Main Menu 🌟"
    
    if user.gender == "boy":
        if user.payment_status == "paid":
            if user.chats_remaining == float('inf'):
                text += f"\n\n💎 Premium (Expires: {user.payment_expiry.strftime('%Y-%m-%d')})"
            else:
                text += f"\n\n🔑 Chats Left: {user.chats_remaining}"
        else:
            text += "\n\n🔒 Purchase a plan to chat with girls"
    
    buttons = []
    if user.gender == "boy" and user.can_chat():
        buttons.append([InlineKeyboardButton("🔍 Find Girl", callback_data='find_match')])
    elif user.gender == "girl":
        buttons.append([InlineKeyboardButton("🔍 Find Boy", callback_data='find_match')])
    
    if user.gender == "boy":
        buttons.append([InlineKeyboardButton("💰 Buy Chats", callback_data='payment_options')])
    
    buttons.append([InlineKeyboardButton("📢 Earn Free Chats", callback_data='refer_friends')])
    
    update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

def button_handler(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    user = user_data.get(user_id)
    
    if not user:
        query.edit_message_text("Session expired. Please /start again.")
        return ConversationHandler.END
    
    if query.data == 'payment_options':
        show_payment_options(query)
    elif query.data == 'refer_friends':
        show_referral_info(query, user)
    elif query.data == 'find_match':
        handle_find_match(query, user)
    elif query.data.startswith('purchase_'):
        handle_purchase(query)
    elif query.data == 'submit_payment':
        query.edit_message_text(
            "💳 Send your Zain/AsiaCell card number:\n\n"
            "Format: /payment CARD_NUMBER\n\n"
            "Example: /payment 1234567890123456"
        )
    elif query.data == 'back_to_menu':
        show_main_menu_from_query(query, context, user_id)
    elif query.data == 'cancel_match':
        handle_cancel_match(query, user)
    
    return MAIN_MENU

def show_payment_options(query):
    buttons = [
        [InlineKeyboardButton(f"🟢 Weekly (${PAYMENT_OPTIONS['weekly']['price']})", callback_data='purchase_weekly')],
        [InlineKeyboardButton(f"🔵 3 Chats (${PAYMENT_OPTIONS['three_chats']['price']})", callback_data='purchase_three_chats')],
        [InlineKeyboardButton("🔙 Back", callback_data='back_to_menu')]
    ]
    query.edit_message_text(
        "💵 Payment Plans:\n\n"
        f"1. {PAYMENT_OPTIONS['weekly']['description']}\n"
        f"2. {PAYMENT_OPTIONS['three_chats']['description']}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

def handle_purchase(query):
    option = query.data.split('_')[1]
    pending_payments[query.from_user.id] = option
    
    query.edit_message_text(
        f"📝 You selected: {PAYMENT_OPTIONS[option]['description']}\n\n"
        "Payment Methods:\n"
        "• Zain Card\n"
        "• AsiaCell Card\n\n"
        "Send your card number with:\n"
        "/payment CARD_NUMBER",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Pay Now", callback_data='submit_payment')],
            [InlineKeyboardButton("🔙 Back", callback_data='payment_options')]
        ])
    )

def payment_received(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    
    if user_id not in pending_payments:
        update.message.reply_text("First select a payment option from the menu")
        return MAIN_MENU
    
    try:
        card_number = context.args[0]
        if not card_number.isdigit() or len(card_number) < 12:
            raise ValueError
    except (IndexError, ValueError):
        update.message.reply_text("Invalid card. Use: /payment CARD_NUMBER")
        return PAYMENT
    
    option = pending_payments[user_id]
    price = PAYMENT_OPTIONS[option]['price']
    
    # Send to your private channel for approval
    context.bot.send_message(
        ORDERS_CHANNEL,
        f"🆕 Payment Request 🆕\n\n"
        f"User: {user_id}\n"
        f"Plan: {option} (${price})\n"
        f"Card: {card_number}\n\n"
        f"/approve_{user_id}\n"
        f"/reject_{user_id}"
    )
    
    update.message.reply_text(
        "⌛ Payment submitted for approval.\n"
        "You'll get a notification when approved."
    )
    
    del pending_payments[user_id]
    return MAIN_MENU

def approve_payment(update: Update, context: CallbackContext):
    if update.message.chat.username != ORDERS_CHANNEL:
        return
    
    try:
        command, user_id = update.message.text.split('_')
        user_id = int(user_id)
        user = user_data[user_id]
        
        if command == '/approve':
            if user.payment_status == "unpaid":
                option = "weekly"  # Default to weekly if not in pending (for manual approvals)
                if user_id in pending_payments:
                    option = pending_payments[user_id]
                
                if option == "weekly":
                    user.activate_weekly()
                else:
                    user.activate_three_chats()
                
                context.bot.send_message(
                    user_id,
                    "✅ Payment Approved!\n\n"
                    "You can now start chatting with girls!"
                )
                update.message.reply_text(f"Approved user {user_id}")
            else:
                update.message.reply_text("User already has active subscription")
        
        elif command == '/reject':
            context.bot.send_message(
                user_id,
                "❌ Payment Rejected\n\n"
                "Please check your card details and try again."
            )
            update.message.reply_text(f"Rejected user {user_id}")
    
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

def show_referral_info(query, user):
    ref_link = f"https://t.me/{(context.bot.username)}?start=ref{user.user_id}"
    
    query.edit_message_text(
        f"📢 Referral Program\n\n"
        f"Your link:\n{ref_link}\n\n"
        "• Get 1 FREE chat per referral\n"
        f"• Your referrals: {user.referrals}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data='back_to_menu')]
        ])
    )

def handle_find_match(query, user):
    if user.gender == "boy" and not user.can_chat():
        query.edit_message_text(
            "❌ You need to buy a plan first",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Buy Plan", callback_data='payment_options')],
                [InlineKeyboardButton("🔙 Back", callback_data='back_to_menu')]
            ])
        )
        return
    
    user.waiting_for_match = True
    match_found = False
    
    # Try to find a match
    for uid, u in user_data.items():
        if (u.gender != user.gender and u.waiting_for_match and 
            uid != user.user_id and (u.gender == "girl" or u.can_chat())):
            # Create match
            user.current_chat = uid
            u.current_chat = user.user_id
            user.waiting_for_match = False
            u.waiting_for_match = False
            match_found = True
            
            # Start chat session
            chat_id = f"{min(user.user_id, uid)}_{max(user.user_id, uid)}"
            active_chats[chat_id] = {
                'start_time': datetime.now(),
                'users': [user.user_id, uid],
                'timer': threading.Timer(900, end_chat_session, [chat_id])  # 15 minutes
            }
            active_chats[chat_id]['timer'].start()
            
            # Notify both users
            context.bot.send_message(
                user.user_id,
                f"💬 Chat started with {u.gender} ({u.age})\n"
                "⏳ 15 minutes\n\n"
                "Type /end to finish early",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ End", callback_data='cancel_match')]
                ])
            )
            
            context.bot.send_message(
                uid,
                f"💬 Chat started with {user.gender} ({user.age})\n"
                "⏳ 15 minutes\n\n"
                "Type /end to finish early",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ End", callback_data='cancel_match')]
                ])
            )
            break
    
    if not match_found:
        query.edit_message_text(
            "🔍 Searching for matches...\n\n"
            "We'll notify you when we find someone!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data='back_to_menu')]
            ])
        )

def end_chat_session(chat_id):
    if chat_id not in active_chats:
        return
    
    user1_id, user2_id = active_chats[chat_id]['users']
    
    # Notify users
    context.bot.send_message(user1_id, "⏰ Chat session ended")
    context.bot.send_message(user2_id, "⏰ Chat session ended")
    
    # Clean up
    if user1_id in user_data:
        user_data[user1_id].current_chat = None
    if user2_id in user_data:
        user_data[user2_id].current_chat = None
    
    if active_chats[chat_id]['timer']:
        active_chats[chat_id]['timer'].cancel()
    
    del active_chats[chat_id]

def handle_cancel_match(query, user):
    if user.current_chat:
        chat_id = f"{min(user.user_id, user.current_chat)}_{max(user.user_id, user.current_chat)}"
        end_chat_session(chat_id)
    elif user.waiting_for_match:
        user.waiting_for_match = False
    
    show_main_menu_from_query(query, context, user.user_id)

def chat_message_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user = user_data.get(user_id)
    
    if not user or not user.current_chat:
        update.message.reply_text("You're not in an active chat. Use /start")
        return
    
    # Forward message to match
    context.bot.send_message(
        user.current_chat,
        f"👤 Anonymous: {update.message.text}"
    )

def show_main_menu_from_query(query, context: CallbackContext, user_id: int):
    show_main_menu(Update(message=query.message), context, user_id)

def error_handler(update: Update, context: CallbackContext):
    logger.error(msg="Exception:", exc_info=context.error)

def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [MessageHandler(Filters.text & ~Filters.command, gender_received)],
            AGE: [MessageHandler(Filters.text & ~Filters.command, age_received)],
            MAIN_MENU: [
                CallbackQueryHandler(button_handler),
                CommandHandler('payment', payment_received),
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, chat_message_handler))
    dp.add_handler(CommandHandler('approve', approve_payment))
    dp.add_handler(CommandHandler('reject', approve_payment))  # Same handler for reject
    dp.add_error_handler(error_handler)

    # Start with webhook
    updater.start_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get('PORT', 5000)),
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )
    updater.idle()

if __name__ == '__main__':
    main()
