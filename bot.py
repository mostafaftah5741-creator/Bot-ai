"""
╔══════════════════════════════════════════════════════╗
║        🤖 بوت تيليجرام - Groq AI                ║
╚══════════════════════════════════════════════════════╝
التثبيت:
    pip install python-telegram-bot openai

التشغيل:
    python bot.py
"""

import os, logging, base64
from datetime import datetime
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ╔══════════════════════════════════════════════════════╗
# ║               ✏️  اكتب بياناتك هنا                  ║
# ╚══════════════════════════════════════════════════════╝

TELEGRAM_BOT_TOKEN = "8688206596:AAFvt12_dhB27xovFTeeMQPf2aB2jHqHGqw"       # من @BotFather
GROQ_API_KEY = "DarkAI-DeepAI-EFF939A9130A0ABAE3A7414D"    # من console.groq.com
ADMIN_ID           = 6918240643                      # معرفك من @userinfobot

# ╔══════════════════════════════════════════════════════╗
# ║          ⚙️  إعدادات يمكنك تعديلها                  ║
# ╚══════════════════════════════════════════════════════╝

GROQ_MODEL  = "llama-3.3-70b-versatile"   # أو "llama-3.1-8b-instant" للسرعة
MAX_HISTORY     = 20                # عدد الرسائل المحفوظة في الذاكرة
MAX_TOKENS      = 2000              # طول الرد الأقصى
BOT_NAME        = "مساعدي الذكي"

BOT_PERSONALITY = """أنت مساعد ذكي ومفيد مدعوم بـ Groq AI.
تتحدث العربية والإنجليزية بطلاقة تامة.
أنت ودود، محترف، ودقيق في إجاباتك.
تستخدم الإيموجي باعتدال."""

# ══════════════════════════════════════════════
#               السجلات
# ══════════════════════════════════════════════
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#           تخزين البيانات (في الذاكرة)
# ══════════════════════════════════════════════
conversation_history : dict = {}   # سجل المحادثات لكل مستخدم
user_stats           : dict = {}   # إحصائيات المستخدمين
banned_users         : set  = set()

ADMIN_IDS = {ADMIN_ID}   # مجموعة المشرفين

personalities = {
    "🤖 مساعد عام":  BOT_PERSONALITY,
    "📚 معلم":        "أنت معلم صبور ومتميز. تشرح المفاهيم ببساطة مع أمثلة عملية.",
    "💻 مبرمج":       "أنت خبير برمجي. تجيب بكود نظيف ومشروح مع أفضل الممارسات.",
    "✍️ كاتب":        "أنت كاتب إبداعي. تساعد في الكتابة والتحرير بأسلوب راقٍ.",
    "🔍 محلل":        "أنت محلل دقيق. تحلل المعلومات وتقدم رؤى منطقية وعميقة.",
    "🌍 مترجم":       "أنت مترجم محترف. تترجم بدقة وتحافظ على أسلوب النص الأصلي.",
}
user_personality: dict = {}


# ══════════════════════════════════════════════
#           محرك Groq AI
# ══════════════════════════════════════════════
class GroqAI:

    @staticmethod
    async def chat(user_id: int, user_message: str) -> str:
        """إرسال رسالة إلى API وحفظ السياق"""
        import asyncio, requests as req

        if user_id not in conversation_history:
            conversation_history[user_id] = []

        personality = personalities.get(
            user_personality.get(user_id, "🤖 مساعد عام"), BOT_PERSONALITY
        )

        conversation_history[user_id].append({"role": "user", "content": user_message})

        # اقتطاع الذاكرة القديمة
        if len(conversation_history[user_id]) > MAX_HISTORY * 2:
            conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY * 2:]

        # بناء السياق كنص
        context = personality + "\n\n"
        for msg in conversation_history[user_id]:
            role = "المستخدم" if msg["role"] == "user" else "المساعد"
            context += f"{role}: {msg['content']}\n"

        try:
            def call_api():
                r = req.post(
                    "https://sii3.top/api/deepseek/api.php",
                    data={"key": GROQ_API_KEY, "v3": context},
                    timeout=60
                )
                try:
                    return r.json().get("response", "") or r.text
                except Exception:
                    return r.text

            reply = await asyncio.to_thread(call_api)
            if not reply:
                reply = "⚠️ لم يصل رد من الـ API."

            conversation_history[user_id].append({"role": "assistant", "content": reply})
            GroqAI._save_stats(user_id)
            return reply

        except Exception as e:
            logger.error(f"API Error [{user_id}]: {e}")
            return f"⚠️ *خطأ في الاتصال:*\n`{str(e)[:300]}`"

    @staticmethod
    async def analyze_image(user_id: int, image_b64: str, caption: str = "") -> str:
        """تحليل صورة باستخدام Groq Vision"""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key  = GROQ_API_KEY,  # unused
                base_url = "https://api.groq.com/openai/v1"
            )
            prompt = caption if caption else "حلل هذه الصورة بالتفصيل واشرح ما تراه."
            resp = await client.chat.completions.create(
                model = "llama-3.3-70b-versatile",
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text",      "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                }],
                max_tokens = MAX_TOKENS,
            )
            reply = resp.choices[0].message.content
            GroqAI._save_stats(user_id)
            return reply
        except Exception as e:
            logger.error(f"Vision Error [{user_id}]: {e}")
            # fallback إذا فشل تحليل الصورة
            return await GroqAI.chat(user_id,
                f"لا أستطيع رؤية الصورة مباشرةً. {caption or 'هل يمكنك وصف ما تريد معرفته؟'}")

    @staticmethod
    def _save_stats(user_id: int):
        if user_id not in user_stats:
            user_stats[user_id] = {"messages": 0, "first_seen": datetime.now().strftime("%Y-%m-%d")}
        user_stats[user_id]["messages"] += 1
        user_stats[user_id]["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M")


# ══════════════════════════════════════════════
#           الأوامر الأساسية
# ══════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("📚 الأوامر",      callback_data="cb_help"),
         InlineKeyboardButton("🎭 الشخصية",      callback_data="cb_personality")],
        [InlineKeyboardButton("📊 إحصائياتي",    callback_data="cb_stats"),
         InlineKeyboardButton("🗑️ مسح الذاكرة", callback_data="cb_clear")],
    ]
    await update.message.reply_text(
        f"👋 *أهلاً {user.first_name}!*\n\n"
        f"أنا *{BOT_NAME}* 🤖\n"
        f"مدعوم بـ *Groq AI* ✨\n\n"
        "*ما يمكنني فعله:*\n"
        "• 💬 محادثة ذكية مع حفظ السياق\n"
        "• 🖼️ تحليل الصور المرسلة\n"
        "• 📄 قراءة الملفات النصية\n"
        "• 🎭 تغيير الشخصية حسب احتياجك\n\n"
        "_فقط أرسل رسالتك وسأرد فوراً!_ 🚀",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *قائمة الأوامر:*\n\n"
        "`/start` — الصفحة الرئيسية\n"
        "`/clear` — مسح ذاكرة المحادثة\n"
        "`/personality` — تغيير شخصية البوت\n"
        "`/stats` — إحصائياتك الشخصية\n"
        "`/info` — معلومات البوت\n"
        "`/help` — هذه القائمة\n\n"
        "👑 *للمشرفين:*\n"
        "`/admin` — لوحة التحكم\n"
        "`/broadcast [رسالة]` — إرسال للجميع\n"
        "`/ban [id]` — حظر مستخدم\n"
        "`/unban [id]` — رفع الحظر\n"
        "`/userlist` — قائمة المستخدمين\n\n"
        "💡 *نصيحة:* أرسل صورة لتحليلها تلقائياً!",
        parse_mode="Markdown"
    )


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    conversation_history.pop(update.effective_user.id, None)
    await update.message.reply_text("🗑️ تم مسح الذاكرة! ابدأ محادثة جديدة 😊")


async def cmd_personality(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid     = update.effective_user.id
    current = user_personality.get(uid, "🤖 مساعد عام")
    keyboard = [
        [InlineKeyboardButton(
            ("✅ " if current == name else "") + name,
            callback_data=f"cb_per_{name}"
        )]
        for name in personalities
    ]
    await update.message.reply_text(
        f"🎭 *اختر شخصية البوت:*\n\nالحالية: *{current}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = user_stats.get(uid, {})
    hist = len(conversation_history.get(uid, [])) // 2
    await update.message.reply_text(
        "📊 *إحصائياتك الشخصية:*\n\n"
        f"👤 المعرف: `{uid}`\n"
        f"💬 إجمالي الرسائل: *{s.get('messages', 0)}*\n"
        f"📝 الجلسة الحالية: *{hist}* رسالة\n"
        f"🎭 الشخصية: *{user_personality.get(uid, '🤖 مساعد عام')}*\n"
        f"📅 أول استخدام: `{s.get('first_seen', 'اليوم')}`\n"
        f"🕐 آخر نشاط: `{s.get('last_seen', 'الآن')}`",
        parse_mode="Markdown"
    )


async def cmd_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    total = sum(s.get("messages", 0) for s in user_stats.values())
    await update.message.reply_text(
        "ℹ️ *معلومات البوت:*\n\n"
        f"🤖 الاسم: *{BOT_NAME}*\n"
        f"🧠 المزود: *Groq AI*\n"
        f"📦 النموذج: `{GROQ_MODEL}`\n"
        f"👥 إجمالي المستخدمين: *{len(user_stats)}*\n"
        f"💬 إجمالي الرسائل: *{total}*\n"
        f"🔄 محادثات نشطة: *{len(conversation_history)}*",
        parse_mode="Markdown"
    )


# ══════════════════════════════════════════════
#         أوامر المشرفين
# ══════════════════════════════════════════════

def admin_only(func):
    """ديكوريتور: يتحقق أن المستخدم مشرف"""
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط.")
            return
        return await func(update, ctx)
    wrapper.__name__ = func.__name__
    return wrapper


@admin_only
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    total = sum(s.get("messages", 0) for s in user_stats.values())
    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات تفصيلية", callback_data="adm_stats")],
        [InlineKeyboardButton("👥 قائمة المستخدمين",  callback_data="adm_users")],
        [InlineKeyboardButton("🚫 قائمة المحظورين",   callback_data="adm_banned")],
    ]
    await update.message.reply_text(
        "👑 *لوحة تحكم المشرف:*\n\n"
        f"👥 المستخدمون: *{len(user_stats)}*\n"
        f"💬 إجمالي الرسائل: *{total}*\n"
        f"🚫 المحظورون: *{len(banned_users)}*\n"
        f"🔄 محادثات نشطة: *{len(conversation_history)}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@admin_only
async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = " ".join(ctx.args)
    if not msg:
        await update.message.reply_text("📢 استخدام: `/broadcast [الرسالة]`", parse_mode="Markdown")
        return
    progress = await update.message.reply_text(f"📢 جاري الإرسال لـ {len(user_stats)} مستخدم...")
    sent = failed = 0
    for uid in list(user_stats.keys()):
        try:
            await ctx.bot.send_message(uid, f"📢 *رسالة من الإدارة:*\n\n{msg}", parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1
    await progress.edit_text(
        f"📢 *اكتمل الإرسال!*\n✅ نجح: {sent}\n❌ فشل: {failed}",
        parse_mode="Markdown"
    )


@admin_only
async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("استخدام: `/ban [user_id]`", parse_mode="Markdown")
        return
    uid = int(ctx.args[0])
    banned_users.add(uid)
    conversation_history.pop(uid, None)
    await update.message.reply_text(f"🚫 تم حظر المستخدم `{uid}` ومسح محادثته.", parse_mode="Markdown")


@admin_only
async def cmd_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("استخدام: `/unban [user_id]`", parse_mode="Markdown")
        return
    uid = int(ctx.args[0])
    banned_users.discard(uid)
    await update.message.reply_text(f"✅ تم رفع الحظر عن `{uid}`.", parse_mode="Markdown")


@admin_only
async def cmd_userlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not user_stats:
        await update.message.reply_text("لا يوجد مستخدمون بعد.")
        return
    lines = [
        f"`{uid}` — {s.get('messages',0)} رسالة — آخر نشاط: {s.get('last_seen','؟')}"
        for uid, s in sorted(user_stats.items(), key=lambda x: x[1].get('messages',0), reverse=True)[:20]
    ]
    await update.message.reply_text(
        "👥 *أكثر 20 مستخدماً نشاطاً:*\n\n" + "\n".join(lines),
        parse_mode="Markdown"
    )


# ══════════════════════════════════════════════
#           معالجات الرسائل
# ══════════════════════════════════════════════

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in banned_users:
        await update.message.reply_text("🚫 أنت محظور من استخدام هذا البوت.")
        return

    text = update.message.text
    logger.info(f"[{uid}] {update.effective_user.first_name}: {text[:80]}")

    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    response = await GroqAI.chat(uid, text)

    # تقسيم الرد إذا كان طويلاً
    for i in range(0, len(response), 4096):
        await update.message.reply_text(response[i:i+4096])


async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in banned_users:
        return

    processing_msg = await update.message.reply_text("🔍 جاري تحليل الصورة... ⏳")
    await ctx.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    try:
        photo   = update.message.photo[-1]          # أعلى جودة
        file    = await ctx.bot.get_file(photo.file_id)
        data    = await file.download_as_bytearray()
        b64     = base64.b64encode(data).decode()
        caption = update.message.caption or ""

        response = await GroqAI.analyze_image(uid, b64, caption)
        await processing_msg.edit_text(
            f"🖼️ *تحليل الصورة:*\n\n{response}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Photo handler error [{uid}]: {e}")
        await processing_msg.edit_text("❌ فشل تحليل الصورة. حاول مرة أخرى.")


async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in banned_users:
        return
    doc = update.message.document
    # قبول النصوص والكود فقط
    allowed_types = ("text/", "application/json", "application/xml")
    if not doc.mime_type or not any(doc.mime_type.startswith(t) for t in allowed_types):
        await update.message.reply_text("📄 أستطيع قراءة الملفات النصية فقط (.txt .py .md .json ...)")
        return

    processing_msg = await update.message.reply_text("📄 جاري قراءة الملف... ⏳")
    try:
        file = await ctx.bot.get_file(doc.file_id)
        raw  = await file.download_as_bytearray()
        text = raw.decode("utf-8", errors="ignore")[:5000]
        prompt   = f"اقرأ هذا الملف ({doc.file_name}) وقدم ملخصاً وتحليلاً له:\n\n{text}"
        response = await GroqAI.chat(uid, prompt)
        await processing_msg.edit_text(
            f"📋 *تحليل الملف ({doc.file_name}):*\n\n{response}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await processing_msg.edit_text(f"❌ فشل قراءة الملف: {e}")


# ══════════════════════════════════════════════
#           معالج الأزرار التفاعلية
# ══════════════════════════════════════════════

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid  = query.from_user.id

    # أزرار عامة
    if data == "cb_help":
        await query.message.reply_text(
            "📚 *الأوامر الرئيسية:*\n\n"
            "`/clear` — مسح الذاكرة\n"
            "`/personality` — تغيير الشخصية\n"
            "`/stats` — إحصائياتك\n"
            "`/help` — القائمة الكاملة",
            parse_mode="Markdown"
        )

    elif data == "cb_personality":
        current  = user_personality.get(uid, "🤖 مساعد عام")
        keyboard = [
            [InlineKeyboardButton(
                ("✅ " if current == name else "") + name,
                callback_data=f"cb_per_{name}"
            )]
            for name in personalities
        ]
        await query.message.reply_text(
            f"🎭 الشخصية الحالية: *{current}*\nاختر شخصية:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("cb_per_"):
        name = data.replace("cb_per_", "")
        if name in personalities:
            user_personality[uid] = name
            conversation_history.pop(uid, None)
            await query.message.reply_text(
                f"✅ تم تغيير الشخصية إلى *{name}*\n"
                f"_تم مسح الذاكرة تلقائياً_",
                parse_mode="Markdown"
            )

    elif data == "cb_stats":
        s    = user_stats.get(uid, {})
        hist = len(conversation_history.get(uid, [])) // 2
        await query.message.reply_text(
            "📊 *إحصائياتك:*\n\n"
            f"💬 إجمالي الرسائل: *{s.get('messages', 0)}*\n"
            f"📝 الجلسة الحالية: *{hist}* رسالة\n"
            f"🎭 الشخصية: *{user_personality.get(uid, '🤖 مساعد عام')}*",
            parse_mode="Markdown"
        )

    elif data == "cb_clear":
        conversation_history.pop(uid, None)
        await query.message.reply_text("🗑️ تم مسح الذاكرة بنجاح!")

    # أزرار المشرفين
    elif data == "adm_stats" and uid in ADMIN_IDS:
        total  = sum(s.get("messages", 0) for s in user_stats.values())
        active = sum(1 for s in user_stats.values() if s.get("last_seen", "")[:10] == datetime.now().strftime("%Y-%m-%d"))
        await query.message.reply_text(
            "📊 *إحصائيات تفصيلية:*\n\n"
            f"👥 إجمالي المستخدمين: *{len(user_stats)}*\n"
            f"🟢 نشطون اليوم: *{active}*\n"
            f"💬 إجمالي الرسائل: *{total}*\n"
            f"🔄 محادثات في الذاكرة: *{len(conversation_history)}*\n"
            f"🚫 المحظورون: *{len(banned_users)}*",
            parse_mode="Markdown"
        )

    elif data == "adm_users" and uid in ADMIN_IDS:
        if not user_stats:
            await query.message.reply_text("لا يوجد مستخدمون بعد.")
            return
        lines = [
            f"`{i}` — {s.get('messages',0)} رسالة"
            for i, s in sorted(user_stats.items(), key=lambda x: x[1].get('messages',0), reverse=True)[:15]
        ]
        await query.message.reply_text(
            "👥 *أكثر المستخدمين نشاطاً:*\n\n" + "\n".join(lines),
            parse_mode="Markdown"
        )

    elif data == "adm_banned" and uid in ADMIN_IDS:
        if not banned_users:
            await query.message.reply_text("✅ لا يوجد مستخدمون محظورون.")
            return
        lines = [f"🚫 `{i}`" for i in banned_users]
        await query.message.reply_text(
            "🚫 *المستخدمون المحظورون:*\n\n" + "\n".join(lines),
            parse_mode="Markdown"
        )


async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error(f"خطأ: {ctx.error}", exc_info=ctx.error)


# ══════════════════════════════════════════════
#           تسجيل الأوامر في تيليجرام
# ══════════════════════════════════════════════

async def post_init(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start",       "الصفحة الرئيسية"),
        BotCommand("help",        "قائمة الأوامر"),
        BotCommand("clear",       "مسح ذاكرة المحادثة"),
        BotCommand("personality", "تغيير شخصية البوت"),
        BotCommand("stats",       "إحصائياتي الشخصية"),
        BotCommand("info",        "معلومات البوت"),
        BotCommand("admin",       "لوحة تحكم المشرف"),
    ])
    logger.info("✅ تم تسجيل الأوامر بنجاح!")


# ══════════════════════════════════════════════
#             الدالة الرئيسية
# ══════════════════════════════════════════════

def main():
    # التحقق من البيانات
    if "اكتب_توكن" in TELEGRAM_BOT_TOKEN:
        print("❌ الخطأ: لم تضع TELEGRAM_BOT_TOKEN!")
        print("   افتح الملف وعدّل السطر:  TELEGRAM_BOT_TOKEN = '...' ")
        return
    if "اكتب_مفتاح" in GROQ_API_KEY:
        print("❌ الخطأ: لم تضع GROQ_API_KEY!")
        print("   احصل عليه من: https://console.groq.com")
        return

    print("""
╔══════════════════════════════════════╗
║    🤖 Groq Telegram Bot         ║
║    جاري التشغيل...                  ║
╚══════════════════════════════════════╝
""")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # أوامر عامة
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("clear",       cmd_clear))
    app.add_handler(CommandHandler("personality", cmd_personality))
    app.add_handler(CommandHandler("stats",       cmd_stats))
    app.add_handler(CommandHandler("info",        cmd_info))

    # أوامر المشرفين
    app.add_handler(CommandHandler("admin",       cmd_admin))
    app.add_handler(CommandHandler("broadcast",   cmd_broadcast))
    app.add_handler(CommandHandler("ban",         cmd_ban))
    app.add_handler(CommandHandler("unban",       cmd_unban))
    app.add_handler(CommandHandler("userlist",    cmd_userlist))

    # معالجات الرسائل
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO,        handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # الأزرار والأخطاء
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    logger.info("🚀 البوت يعمل! اضغط Ctrl+C للإيقاف.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
