import os
import sqlite3
import google.generativeai as genai
from flask import Flask
from threading import Thread
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# --- مشغل وهمي لخدمة الويب (لإرضاء Render) ---
app = Flask('')
@app.route('/')
def home(): return "البوت يعمل بنجاح!"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- الإعدادات ---
BOT_TOKEN = "8566636106:AAFnFZNn6l_6ub_LsZo5xO5AbjqXsVNEId0"
MY_USER_ID = 298015369
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
    if update.message and update.message.new_chat_members:
        chat_id = update.effective_chat.id
        welcome_status = db_action('SELECT welcome_on FROM settings WHERE chat_id = ?', (chat_id,), True)
        if welcome_status is None or welcome_status[0] == 1:
            for member in update.message.new_chat_members:
                await update.message.reply_text(f"مرحباً بك يا {member.first_name} نورتنا ✨")
        return

    if not update.message or not update.message.text: return
    text = update.message.text.strip()
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    member = await context.bot.get_chat_member(chat_id, user_id)
    is_authorized = member.status in ['creator', 'administrator'] or user_id == MY_USER_ID

    if is_authorized:
        if text == "قفل التحويل":
            db_action('INSERT OR REPLACE INTO settings (chat_id, lock_forward, welcome_on) VALUES (?, 1, 1)', (chat_id,))
            await update.message.reply_text("🔒 تم قفل التحويل.")
        elif text == "فتح التحويل":
            db_action('UPDATE settings SET lock_forward = 0 WHERE chat_id = ?', (chat_id,))
            await update.message.reply_text("🔓 تم فتح التحويل.")
        elif text == "الاوامر":
            await update.message.reply_text("📋 أوامر الإدارة: مسح، ثبت، حظر، كتم، قفل التحويل/الترحيب.")

    if text == "بوت":
        await update.message.reply_text("لبيه ياعيونه 🫡")

if __name__ == '__main__':
    keep_alive() # تشغيل الموقع الوهمي
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, handle_everything))
    application.run_polling()
