import logging
import sqlite3
import google.generativeai as genai
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- الإعدادات (تم وضع بياناتك هنا) ---
BOT_TOKEN = "8566636106:AAFnFZNn6l_6ub_LsZo5xO5AbjqXsVNEId0"
MY_USER_ID = 298015369  # آيدي هاشم المفلحي
genai.configure(api_key="AIzaSyA5pzOpKVcMGm6Aek82KoB3Pk94dYg3LX4")
model = genai.GenerativeModel('gemini-pro')

# --- قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('management_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (chat_id INTEGER PRIMARY KEY, lock_forward INTEGER DEFAULT 0, welcome_on INTEGER DEFAULT 1)''')
    conn.commit()
    conn.close()

def db_action(query, params=(), fetch=False):
    conn = sqlite3.connect('management_bot.db')
    c = conn.cursor()
    c.execute(query, params)
    res = c.fetchone() if fetch else None
    conn.commit()
    conn.close()
    return res

init_db()

async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. الترحيب بالأعضاء الجدد
    if update.message and update.message.new_chat_members:
        chat_id = update.effective_chat.id
        welcome_status = db_action('SELECT welcome_on FROM settings WHERE chat_id = ?', (chat_id,), True)
        if welcome_status is None or welcome_status[0] == 1:
            for member in update.message.new_chat_members:
                await update.message.reply_text(f"مرحباً بك يا {member.first_name} في مجموعتنا! نورتنا ✨")
        return

    if not update.message or not update.message.text: return
    
    text = update.message.text.strip()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # التحقق من الصلاحية (أنت أو مشرف في التليجرام)
    member = await context.bot.get_chat_member(chat_id, user_id)
    is_authorized = member.status in ['creator', 'administrator'] or user_id == MY_USER_ID

    # 2. حماية التحويل
    lock_forward = db_action('SELECT lock_forward FROM settings WHERE chat_id = ?', (chat_id,), True)
    if update.message.forward_date and lock_forward and lock_forward[0] == 1 and not is_authorized:
        try:
            await update.message.delete()
            return
        except: pass

    # --- أوامر المشرفين وهاشم ---
    if is_authorized:
        if text == "قفل التحويل":
            db_action('INSERT OR REPLACE INTO settings (chat_id, lock_forward, welcome_on) VALUES (?, 1, (SELECT welcome_on FROM settings WHERE chat_id=?))', (chat_id, chat_id))
            await update.message.reply_text("🔒 تم قفل التحويل.")
        elif text == "فتح التحويل":
            db_action('UPDATE settings SET lock_forward = 0 WHERE chat_id = ?', (chat_id,))
            await update.message.reply_text("🔓 تم فتح التحويل.")
        elif text == "قفل الترحيب":
            db_action('INSERT OR REPLACE INTO settings (chat_id, lock_forward, welcome_on) VALUES (?, (SELECT lock_forward FROM settings WHERE chat_id=?), 0)', (chat_id, chat_id))
            await update.message.reply_text("🔕 تم إيقاف الترحيب.")
        elif text == "فتح الترحيب":
            db_action('UPDATE settings SET welcome_on = 1 WHERE chat_id = ?', (chat_id,))
            await update.message.reply_text("🔔 تم تفعيل الترحيب.")

        # التثبيت والمسح
        if update.message.reply_to_message:
            if text == "ثبت":
                await context.bot.pin_chat_message(chat_id, update.message.reply_to_message.message_id)
            elif text == "الغاء تثبيت":
                await context.bot.unpin_chat_message(chat_id, update.message.reply_to_message.message_id)
            elif text == "حظر":
                await context.bot.ban_chat_member(chat_id, update.message.reply_to_message.from_user.id)
            elif text == "كتم":
                await context.bot.restrict_chat_member(chat_id, update.message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=False))

        if text.startswith("مسح "):
            try:
                num = int(text.split()[1])
                await context.bot.delete_message(chat_id, update.message.message_id)
                async for msg in context.bot.get_chat_history(chat_id, limit=num):
                    try: await context.bot.delete_message(chat_id, msg.message_id)
                    except: pass
            except: pass

    # --- التفاعل العام ---
    if text == "الاوامر" and is_authorized:
        await update.message.reply_text(
            "📋 **أوامر الإدارة:**\n"
            "• `قفل الترحيب` / `فتح الترحيب`\n"
            "• `قفل التحويل` / `فتح التحويل`\n"
            "• `مسح + العدد`\n"
            "• `ثبت` / `الغاء تثبيت`\n"
            "• `حظر` / `كتم` (بالرد)\n"
            "• `ايدي` / `بوت`", parse_mode='Markdown'
        )
    elif text == "بوت":
        await update.message.reply_text("لبيه ياعيونه 🫡")
    elif text == "ايدي":
        await update.message.reply_text(f"🆔 آيديك: `{user_id}`")
    elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
        res = model.generate_content(text)
        await update.message.reply_text(res.text)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_everything))
    app.run_polling()
