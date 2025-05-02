import sqlite3
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# إعدادات البوت
API_ID = 12345678  # ضع API ID من my.telegram.org
API_HASH = "your_api_hash"  # ضع API HASH
BOT_TOKEN = "7551982212:AAHSgM4JuGnOBBzafGqGFZhY1-gwVo7g4nY"
CHANNEL_USERNAME = "@invite2earnn"
ORDER_CHANNEL = "@invite2orders"

app = Client("invite2earnn", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# قاعدة البيانات
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (user_id INTEGER PRIMARY KEY, 
              username TEXT, 
              code TEXT, 
              balance REAL, 
              referrals INTEGER, 
              left_referrals INTEGER)''')
conn.commit()

# توليد كود فريد
def generate_code(user_id):
    return f"C{user_id}D"

# التحقق من الاشتراك بالقناة
async def check_subscription(client, user_id):
    try:
        member = await client.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

# القائمة الرئيسية
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("شراء كود الربح الخاص بي", callback_data="buy_code")],
        [InlineKeyboardButton("ربّحني الآن $", callback_data="share_link")],
        [InlineKeyboardButton("اسحب أموالي الآن", callback_data="withdraw")]
    ])

# بدء البوت
@app.on_message(filters.command("start"))
async def start(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "None"
    
    subscribed = await check_subscription(client, user_id)
    if not subscribed:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("الاشتراك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("تم الاشتراك ✅", callback_data="check_sub")]
        ])
        await message.reply("لبدء استخدام البوت يجب عليك الاشتراك بالقناة @invite2earnn", reply_markup=keyboard)
        return
    
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", 
                 (user_id, username, "", 0.0, 0, 0))
        conn.commit()
    
    code = generate_code(user_id)
    c.execute("UPDATE users SET code = ? WHERE user_id = ?", (code, user_id))
    conn.commit()
    
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = c.fetchone()[0]
    
    await message.reply(
        f"1. اسم المستخدم: @{username}\n2. المبلغ الإجمالي: {balance:.2f}$\n3. كود الربح الخاص بك: {code}",
        reply_markup=main_menu()
    )

# تحقق من الاشتراك بعد الضغط على تم الاشتراك
@app.on_callback_query(filters.regex("check_sub"))
async def recheck_subscription(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    subscribed = await check_subscription(client, user_id)
    if subscribed:
        await callback_query.message.delete()
        await start(client, callback_query.message)
    else:
        await callback_query.answer("يرجى الاشتراك أولاً.", show_alert=True)

# شراء كود
@app.on_callback_query(filters.regex("buy_code"))
async def buy_code(client, callback_query: CallbackQuery):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("أسيا سيل", callback_data="pay_asiacell")],
        [InlineKeyboardButton("زين العراق", callback_data="pay_zain")],
        [InlineKeyboardButton("رجوع", callback_data="back")]
    ])
    await callback_query.message.edit_text(
        "اختر طريقة الدفع لشراء كود الربح الخاص بك مقابل 2$:",
        reply_markup=keyboard
    )

# طرق الدفع
@app.on_callback_query(filters.regex("pay_(asiacell|zain)"))
async def process_payment(client, callback_query: CallbackQuery):
    method = callback_query.data.split("_")[1]
    await callback_query.message.edit_text(
        f"ارسل الآن رصيد {method} بقيمة 2$، ثم أرسل رقم الهاتف المرسل منه."
    )

@app.on_message(filters.private & filters.text)
async def get_payment_info(client, message):
    user_id = message.from_user.id
    username = message.from_user.username or "None"
    c.execute("SELECT code FROM users WHERE user_id = ?", (user_id,))
    code = c.fetchone()[0]
    
    await client.send_message(
        ORDER_CHANNEL,
        f"طلب شراء كود:\nالمستخدم: @{username}\nالرقم: {message.text}\nالكود: {code}"
    )
    await client.send_message(ORDER_CHANNEL, code)  # إرسال الكود كرسالة منفصلة
    await message.reply("تم إرسال طلبك، سيتم التواصل معك بعد التحقق.")

# مشاركة رابط دعوة
@app.on_callback_query(filters.regex("share_link"))
async def share_link(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    c.execute("SELECT code FROM users WHERE user_id = ?", (user_id,))
    code = c.fetchone()[0]
    await callback_query.message.edit_text(
        f"شارك هذا الرابط مع أصدقائك: \nhttps://t.me/{app.me.username}?start={code}\n"
        "كل شخص يدخل من رابطك ويشترك بالقناة تكسب 0.1$",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("رجوع", callback_data="back")]
        ])
    )

# سحب الأرباح
@app.on_callback_query(filters.regex("withdraw"))
async def withdraw_request(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("اكتب كود الربح الخاص بك للتحقق:")

@app.on_message(filters.private & filters.text)
async def process_withdraw(client, message):
    user_id = message.from_user.id
    code_entered = message.text.strip()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user or user[2] != code_entered:
        await message.reply("الكود غير صحيح.")
        return
    
    balance = user[3]
    if balance < 2.0:
        await message.reply("يجب أن يكون لديك على الأقل 2$ للسحب.")
        return
    
    await message.reply(
        f"تفاصيل السحب:\nالكود: {user[2]}\nالرصيد: {balance:.2f}$\n"
        f"الإحالات: {user[4]}\nالإلغاء: {user[5]}\nسيتم التواصل معك قريباً.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("زين العراق", callback_data="withdraw_zain")],
            [InlineKeyboardButton("أسيا سيل", callback_data="withdraw_asiacell")],
            [InlineKeyboardButton("ماستر كارد/كي كارد", callback_data="withdraw_card")],
            [InlineKeyboardButton("عملة رقمية", callback_data="withdraw_crypto")]
        ])
    )
    await client.send_message(
        ORDER_CHANNEL,
        f"طلب سحب جديد:\nالمستخدم: @{user[1]}\nالرصيد: {balance:.2f}$\n"
        f"الكود: {user[2]}\nيرجى مراجعة الطلب."
    )

# رجوع
@app.on_callback_query(filters.regex("back"))
async def go_back(client, callback_query: CallbackQuery):
    await start(client, callback_query.message)

print("البوت يعمل بنجاح.")
app.run()
