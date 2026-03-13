import logging
import asyncio
from telegram import Update, Poll
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, PollAnswerHandler

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- بياناتك الخاصة ---
BOT_TOKEN = "8566636106:AAFnFZNn6l_6ub_LsZo5xO5AbjqXsVNEId0"
MY_USER_ID = 298015369

# بيانات المسابقة المؤقتة
quiz_data = {
    "questions": [],
    "scores": {},
    "is_running": False,
    "delay": 15, 
}

# التحقق من الصلاحيات
async def is_admin_or_dev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == MY_USER_ID:
        return True
    if update.effective_chat.type in ['group', 'supergroup']:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return member.status in ['creator', 'administrator']
    return False

# استقبال الأسئلة في الخاص
async def add_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        text = update.message.text
        if "|" in text:
            try:
                parts = text.split("|")
                q_text = parts[0].strip()
                options = [o.strip() for o in parts[1].split(",")]
                correct_id = int(parts[2].strip())
                quiz_data["questions"].append({"question": q_text, "options": options, "correct": correct_id})
                await update.message.reply_text(f"✅ تم إضافة السؤال رقم {len(quiz_data['questions'])}")
            except:
                await update.message.reply_text("⚠️ التنسيق: السؤال | خيار1, خيار2 | 0")

# ضبط المهلة
async def set_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin_or_dev(update, context):
        try:
            seconds = int(context.args[0])
            quiz_data["delay"] = seconds
            await update.message.reply_text(f"⏱️ تم ضبط المهلة لـ {seconds} ثانية.")
        except:
            await update.message.reply_text("⚠️ مثال: /delay 20")

# بدء المسابقة
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_dev(update, context): return
    if not quiz_data["questions"]:
        await update.message.reply_text("⚠️ القائمة فارغة! أضف أسئلة في الخاص أولاً.")
        return
    
    quiz_data["is_running"] = True
    await update.message.reply_text(f"🚀 ستبدأ المسابقة! المهلة: {quiz_data['delay']} ثانية.")

    for i, q in enumerate(quiz_data["questions"]):
        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=f"س {i+1}: {q['question']}",
            options=q['options'],
            type=Poll.QUIZ,
            correct_option_id=q['correct'],
            is_anonymous=False
        )
        await asyncio.sleep(quiz_data["delay"])

    results = "🏆 النتائج النهائية:\n"
    sorted_scores = sorted(quiz_data["scores"].items(), key=lambda x: x[1], reverse=True)
    for name, score in sorted_scores:
        results += f"👤 {name}: {score} نقطة\n"
    
    await update.message.reply_text(results if sorted_scores else "🔚 انتهت المسابقة ولم يشارك أحد.")
    quiz_data["questions"], quiz_data["scores"], quiz_data["is_running"] = [], {}, False

# تتبع الإجابات
async def track_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    user_name = answer.user.full_name
    quiz_data["scores"][user_name] = quiz_data["scores"].get(user_name, 0) + 10

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start_quiz", start_quiz))
    app.add_handler(CommandHandler("delay", set_delay))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), add_question))
    app.add_handler(PollAnswerHandler(track_answer))
    print("البوت يعمل الآن يا هاشم...")
    app.run_polling()
