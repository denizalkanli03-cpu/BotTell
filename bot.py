import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

# ================= SERVER FOR RENDER (KEEP ALIVE) =================
app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "Bot is Alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

# ================= CONFIG =================
TOKEN = "8558196271:AAGsm4xqHnFeT7avPKcOVJvcy5pWrq5ZlN0"
ADMIN_ID = 7997819976
CHANNEL_ID = "@UniVoiceHub"
BOT_USERNAME = "@UniEchoFeedbackBot"
CHANNEL_DIRECT_LINK = "https://t.me/UniVoiceHub?direct"
CHANNEL_TAG = "@UniVoiceHub"

# ================= STATES =================
(SELECT_UNI, ASK_OTHER_UNI, ASK_PROF, ASK_COURSE, ASK_TEACHING, ASK_ETHICS, ASK_NOTES,
 ASK_PROJECT, ASK_ATTEND, ASK_MIDTERM, ASK_FINAL, ASK_MATCH,
 ASK_CONTACT, ASK_CONCLUSION, ASK_SEMESTER, ASK_GRADE) = range(16)

# ================= FORM QUESTIONS =================
FORM_QUESTIONS = [
    ("👨‍🏫 استاد", "استاد"), ("📚 درس", "درس"), ("🎓 نوع تدریس", "نوع تدریس"),
    ("💬 خصوصیات اخلاقی", "خصوصیات اخلاقی"), ("📄 جزوه", "جزوه"), ("🧪 پروژه", "پروژه"),
    ("🕒 حضور و غیاب", "حضور و غیاب"), ("📝 میان‌ترم", "میان‌ترم"), ("📘 پایان‌ترم", "پایان‌ترم"),
    ("📊 تطبیق سوالات", "تطبیق سوالات"), ("📞 راه ارتباطی", "راه ارتباطی"),
    ("📌 نتیجه‌گیری", "نتیجه‌گیری"), ("📅 ترم", "ترم"), ("⭐️ نمره", "نمره"),
]

post_reactions = {}
active_chats = {}
reply_sessions = {}

# ================= HELPERS =================
def reaction_keyboard(msg_id):
    data = post_reactions.get(msg_id, {"likes": set(), "dislikes": set()})
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"👍 {len(data['likes'])}", callback_data=f"like:{msg_id}"),
         InlineKeyboardButton(f"👎 {len(data['dislikes'])}", callback_data=f"dislike:{msg_id}")],
        [InlineKeyboardButton("📝 ثبت نظر", url=f"https://UniEchoFeedbackBot?start=form")]
    ])

def build_form_text(data):
    lines = [f"🏛 **دانشگاه:**\n{data.get('university', '-')}\n"]
    for title, key in FORM_QUESTIONS:
        value = data.get(key, "-")
        lines.append(f"*{title}:*\n{value}\n")
    lines.extend(["──────────────", f"🆔 {CHANNEL_TAG}"])
    return "\n".join(lines)

def cancel_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف و لغو فرم", callback_data="delete_form")]])

def type_selection_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛 دانشگاه‌های دولتی", callback_data="list_gov")],
        [InlineKeyboardButton("🏢 دانشگاه‌های آزاد", callback_data="list_azad")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
    ])

def generate_uni_keyboard(unis):
    keyboard = []
    # ایجاد ۳ ستون در حداکثر ۶ سطر (۱۸ دانشگاه)
    for i in range(0, min(len(unis), 18), 3):
        row = [InlineKeyboardButton(u, callback_data=f"setuni:{u}") for u in unis[i:i+3]]
        keyboard.append(row)
    # سطر هفتم: دکمه‌های کنترلی
    keyboard.append([InlineKeyboardButton("🔍 سایر واحدها", callback_data="setuni:OTHER")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="start_form")])
    return InlineKeyboardMarkup(keyboard)

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if context.args and context.args[0] == "form":
        return await start_form(update, context)

    keyboard = [
        [InlineKeyboardButton("📝 ثبت نظر درباره استاد", callback_data="start_form")],
        [InlineKeyboardButton("💬 چت خصوصی", url=CHANNEL_DIRECT_LINK)],
        [InlineKeyboardButton("🕵️ چت ناشناس با ادمین", callback_data="anon_start")]
    ]
    text = """🎓 به ربات نظرات دانشجویی خوش اومدی!

اینجا یه فضای سراسریه برای همه دانشجوهای دانشگاه‌های کشور تا تجربه‌هاشون رو درباره:

👨🏻‍🏫 اساتید
📚 نحوه تدریس
📝 امتحان‌ها
📊 نمره‌دهی
و فضای درسی

با بقیه به اشتراک بذارن.

هدف ما اینه که قبل از انتخاب واحد یا برداشتن درس، بتونی با آگاهی بیشتر تصمیم بگیری — بر اساس تجربه واقعی بقیه دانشجوها، نه حدس و شنیده‌ها.

🔎 چطور نظرها رو پیدا کنی؟
داخل چنل کافیه:
اسم دانشگاه یا استاد رو جستجو کنی تا همه نظرهای ثبت‌شده برات بیاد.

✍🏻 تو هم می‌تونی تجربه‌ت رو ثبت کنی و به بقیه کمک کنی انتخاب بهتری داشته باشن.

🤝 لطفاً محترمانه و منصفانه نظر بده تا این فضا برای همه مفید و قابل اعتماد بمونه.

موفق باشی تو مسیر دانشگاه ✨"""
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def start_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🏛 **انتخاب دانشگاه**\n\nنوع دانشگاه خود را انتخاب کنید:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(text, reply_markup=type_selection_keyboard(), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=type_selection_keyboard(), parse_mode="Markdown")
    return SELECT_UNI

async def uni_menu_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "list_gov":
        unis = ["تهران", "شریف", "امیرکبیر", "بهشتی", "علم و صنعت", "علامه", "خواجه نصیر", "الزهرا", "خوارزمی", "هنر تهران", "فرهنگیان", "فردوسی", "صنعتی اصفهان", "تبریز", "شیراز", "گیلان", "مازندران", "یزد"]
        await query.message.edit_text("🏛 دانشگاه‌های دولتی:", reply_markup=generate_uni_keyboard(unis))
    elif query.data == "list_azad":
        unis = ["علوم تحقیقات", "تهران مرکزی", "تهران جنوب", "تهران شمال", "تهران غرب", "پزشکی آزاد", "کرج", "رودهن", "پرند", "نجف‌آباد", "تبریز آزاد", "مشهد آزاد", "اصفهان آزاد", "شیراز آزاد", "قزوین آزاد"]
        await query.message.edit_text("🏢 واحدهای دانشگاه آزاد:", reply_markup=generate_uni_keyboard(unis))
    return SELECT_UNI

async def set_university(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uni_name = query.data.split(":")[1]
    if uni_name == "OTHER":
        await query.message.edit_text("🔍 **نام دانشگاه خود را تایپ کنید:**", reply_markup=cancel_markup(), parse_mode="Markdown")
        return ASK_OTHER_UNI
    context.user_data["university"] = uni_name
    await query.message.edit_text(f"✅ دانشگاه **{uni_name}** انتخاب شد.\n\n👨‍🏫 *نام استاد:*", reply_markup=cancel_markup(), parse_mode="Markdown")
    return ASK_PROF

async def ask_other_uni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["university"] = update.message.text
    await update.message.reply_text("👨‍🏫 **نام استاد:**\n\nلطفاً نام استاد را وارد کنید:", reply_markup=cancel_markup(), parse_mode="Markdown")
    return ASK_PROF

# --- مابقی توابع فرم (ask_course تا ask_grade) دقیقاً مطابق کد شما ---
async def ask_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["استاد"] = update.message.text
    await update.message.reply_text("📚 *عنوان درس:*\n\nنام درس را وارد کنید:", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_COURSE

async def ask_teaching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["درس"] = update.message.text
    await update.message.reply_text("🎓 *شیوه تدریس:*\n\nنحوه تدریس استاد چطور بود؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_TEACHING

async def ask_ethics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["نوع تدریس"] = update.message.text
    await update.message.reply_text("💬 *اخلاق و برخورد:*\n\nبرخورد استاد با دانشجوها چطور بود؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_ETHICS

async def ask_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["خصوصیات اخلاقی"] = update.message.text
    await update.message.reply_text("📄 *وضعیت جزوه:*\n\nآیا استاد جزوه کامل می‌دهد؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_NOTES

async def ask_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["جزوه"] = update.message.text
    await update.message.reply_text("🧪 *پروژه و کار عملی:*\n\nآیا این درس پروژه داشت؟ نمره‌دهی چطور بود؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_PROJECT

async def ask_attend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["پروژه"] = update.message.text
    await update.message.reply_text("🕒 *حضور و غیاب:*\n\nوضعیت حضور غیاب و حساسیت استاد؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_ATTEND

async def ask_midterm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["حضور و غیاب"] = update.message.text
    await update.message.reply_text("📝 *امتحان میان‌ترم:*\n\nامتحان میان‌ترم چطور بود؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_MIDTERM

async def ask_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["میان‌ترم"] = update.message.text
    await update.message.reply_text("📘 *امتحان پایان‌ترم:*\n\nسطح سوالات پایان‌ترم؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_FINAL

async def ask_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["پایان‌ترم"] = update.message.text
    await update.message.reply_text("📊 *تطبیق با جزوه (۱ تا ۵):*\n\nتطبیق سوالات با جزوه چطور بود؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_MATCH

async def ask_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["تطبیق سوالات"] = update.message.text
    await update.message.reply_text("📞 *راه ارتباطی:*\n\nنحوه پاسخگویی و ارتباط با استاد؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_CONTACT

async def ask_conclusion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["راه ارتباطی"] = update.message.text
    await update.message.reply_text("📌 *نتیجه‌گیری:*\n\nدر کل این استاد را پیشنهاد می‌کنید؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_CONCLUSION

async def ask_semester(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["نتیجه‌گیری"] = update.message.text
    await update.message.reply_text("📅 *ترم تحصیلی:*\n\nچه ترمی با این استاد داشتید؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_SEMESTER

async def ask_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ترم"] = update.message.text
    await update.message.reply_text("⭐️ *نمره نهایی:*\n\nنمره‌ای که گرفتید (از ۲۰)؟", parse_mode="Markdown", reply_markup=cancel_markup())
    return ASK_GRADE

async def finish_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["نمره"] = update.message.text
    summary = build_form_text(context.user_data)
    keyboard = [[InlineKeyboardButton("✅ ارسال نهایی", callback_data="submit_form")],
                [InlineKeyboardButton("🗑 لغو و حذف", callback_data="delete_form")]]
    await update.message.reply_text(f"🌈 *پیش‌نمایش فرم شما:*\n\n{summary}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return ConversationHandler.END

# ================= سایر بخش‌ها (Admin, Anon, Main) مطابق کد شما با اصلاحات جزیی =================

async def submit_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    summary = build_form_text(context.user_data)
    kb = [[InlineKeyboardButton("✅ تایید انتشار", callback_data=f"admin_accept:{query.from_user.id}"),
           InlineKeyboardButton("❌ رد فرم", callback_data=f"admin_reject:{query.from_user.id}")]]
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📥 فرم جدید:\n\n{summary}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    await query.message.edit_text("📨/start فرم شما برای ادمین ارسال شد. پس از بررسی در کانال منتشر می‌شود.")

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, user_id = query.data.split(":")
    if action == "admin_accept":
        text = query.message.text.replace("📥 فرم جدید:\n\n", "")
        msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="Markdown")
        post_reactions[msg.message_id] = {"likes": set(), "dislikes": set()}
        await msg.edit_reply_markup(reply_markup=reaction_keyboard(msg.message_id))
        await context.bot.send_message(chat_id=user_id, text="✅ نظر شما در کانال منتشر شد.")
    await query.message.delete()

async def delete_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("❌/start عملیات لغو شد.")
    return ConversationHandler.END

# ================= GLOBAL SESSIONS =================
active_chats = {}  # user_id -> True (نشست‌های فعال چت)
reply_sessions = {} # admin_id -> target_user_id
post_reactions = {}
# ================= ANON CHAT HANDLERS =================

async def anon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    user_id = update.callback_query.from_user.id
    active_chats[user_id] = True  # شروع نشست چت
    
    keyboard = [[InlineKeyboardButton("❌ پایان چت ناشناس", callback_data="end_chat")]]
    await update.callback_query.message.reply_text(
        "🕵️ وارد حالت ناشناس شدی.\nهر پیامی بفرستی برای ادمین ارسال می‌شه. برای خروج دکمه زیر رو بزن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id in active_chats:
        del active_chats[user_id]
    
    # اگر ادمین چت را بست
    if user_id == ADMIN_ID and user_id in reply_sessions:
        target_id = reply_sessions[user_id]
        if target_id in active_chats: del active_chats[target_id]
        await context.bot.send_message(chat_id=target_id, text="🔚/start ادمین به این گفتگو پایان داد.")
        del reply_sessions[user_id]

    await query.message.edit_text("✅ چت پایان یافت. برای شروع مجدد /start را بزنید.")

async def receive_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    # ۱. اگر ادمین پیامی بفرستد و در حال پاسخ به کسی باشد
    if user_id == ADMIN_ID and user_id in reply_sessions:
        target_id = reply_sessions[user_id]
        
        # کیبورد برای کاربر (شامل دکمه پاسخ و پایان)
        user_keyboard = [
            [InlineKeyboardButton("✉️ پاسخ به ادمین", callback_data="anon_start")], # بازنشانی حالت چت اگر قطع شده باشد
            [InlineKeyboardButton("❌ پایان چت", callback_data="end_chat")]
        ]
        
        try:
            await context.bot.send_message(
                chat_id=target_id, 
                text=f"📩 **پیام جدید از طرف ادمین:**\n\n{update.message.text}",
                reply_markup=InlineKeyboardMarkup(user_keyboard),
                parse_mode="Markdown"
            )
            await update.message.reply_text(f"✅ پیام شما به کاربر `{target_id}` تحویل داده شد.")
        except:
            await update.message.reply_text("❌ خطا: امکان ارسال پیام به کاربر وجود ندارد (شاید ربات را بلاک کرده باشد).")
        return

    # ۲. اگر کاربر عادی در حالت چت فعال باشد
    if active_chats.get(user_id):
        username = f"@{user.username}" if user.username else "بدون یوزرنیم"
        
        # کیبورد برای ادمین
        admin_keyboard = [
            [InlineKeyboardButton("✉️ پاسخ به این کاربر", callback_data=f"reply_to:{user_id}")],
            [InlineKeyboardButton("❌ قطع دسترسی کاربر", callback_data="end_chat")]
        ]
        
        admin_info = (
            f"🕵️ **پیام ناشناس جدید**\n"
            f"👤 **فرستنده:** {user.full_name}\n"
            f"🆔 `{user_id}` | {username}\n"
            f"────────────────\n"
            f"📝 **متن:** {update.message.text}"
        )
        
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text=admin_info, 
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
        
        # تاییدیه برای کاربر (با دکمه پایان برای اطمینان)
        user_status_keyboard = [[InlineKeyboardButton("❌ پایان گفتگو", callback_data="end_chat")]]
        await update.message.reply_text(
            "🚀 پیام شما با موفقیت به ادمین رسید.\nشما می‌توانید پیام‌های بعدی خود را همینجا بفرستید یا چت را تمام کنید:",
            reply_markup=InlineKeyboardMarkup(user_status_keyboard)
        )

async def admin_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    target_id = int(update.callback_query.data.split(":")[1])
    reply_sessions[ADMIN_ID] = target_id
    await update.callback_query.message.reply_text(f"✍️ در حال پاسخ به `{target_id}` هستید. پیام خود را بفرستید:")

# ================= MAIN =================


def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_form, pattern="^start_form$"), CommandHandler("start", start)],
        states={
            SELECT_UNI: [CallbackQueryHandler(uni_menu_manager, pattern="^(list_gov|list_azad)$"),
                         CallbackQueryHandler(set_university, pattern="^setuni:"),
                         CallbackQueryHandler(start_form, pattern="^start_form$")],
            ASK_OTHER_UNI: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_other_uni)],
            ASK_PROF: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_course)],
            ASK_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_teaching)],
            ASK_TEACHING: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_ethics)],
            ASK_ETHICS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_notes)],
            ASK_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_project)],
            ASK_PROJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_attend)],
            ASK_ATTEND: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_midterm)],
            ASK_MIDTERM: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_final)],
            ASK_FINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_match)],
            ASK_MATCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact)], 
            ASK_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_conclusion)],
            ASK_CONCLUSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_semester)],
            ASK_SEMESTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_grade)],
            ASK_GRADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_form)],
        },
        fallbacks=[CallbackQueryHandler(delete_form, pattern="^delete_form$"), CommandHandler("start", start)]
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(submit_form, pattern="^submit_form$"))
    app.add_handler(CallbackQueryHandler(admin_actions, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(anon_start, pattern="^anon_start$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: reply_sessions.update({ADMIN_ID: int(u.callback_query.data.split(":")[1])}) or u.callback_query.message.reply_text("پاسخ را بنویسید:"), pattern="^reply_to:"))
    app.add_handler(CallbackQueryHandler(end_chat, pattern="^end_chat$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_msg))

    print("✅ ربات با قابلیت انتخاب دانشگاه آنلاین شد!")
    app.run_polling()

if __name__ == "__main__":

    main()




