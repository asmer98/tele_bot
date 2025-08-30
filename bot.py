import os
import yt_dlp
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 🔑 التوكن يجي من متغير بيئة (ماكو داخل الكود)
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@p_y_hy"
COOKIES_FILE = "cookies.txt"  # مسار ملف الكوكيز

# 📝 إعدادات الـ logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ──────────── الأوامر ────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(update, context):
        await update.message.reply_text(
            f"⚠️ حتى تقدر تستخدم البوت، اشترك أولًا بالقناة: {CHANNEL_USERNAME}"
        )
        return

    await update.message.reply_text(
        "👋 أهلاً بيك! أرسل لي رابط الفيديو من أي منصة وأنا أحمله إلك 🎥"
    )

async def is_subscribed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يتأكد من أن المستخدم مشترك بالقناة"""
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من الاشتراك: {e}")
        return False

def download_video(url: str) -> str:
    """تحميل الفيديو وإرجاع المسار"""
    ydl_opts = {
        "format": "best",
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,  # إضافة الكوكيز إذا الملف موجود
        "quiet": True,  # تقليل الإخراج في السجلات
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # تسجيل معلومات عن الفيديو الذي تم تحميله
            logger.info(f"تم تحميل: {info.get('title', 'unknown title')}")
            logger.info(f"تم الحفظ في: {filename}")
            
            return filename
            
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"خطأ في التحميل: {e}")
        raise Exception(f"خطأ في التحميل: {str(e)}")
    except Exception as e:
        logger.error(f"خطأ غير متوقع: {e}")
        raise Exception(f"حدث خطأ غير متوقع: {str(e)}")

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(update, context):
        await update.message.reply_text(
            f"⚠️ حتى تقدر تستخدم البوت، اشترك أولًا بالقناة: {CHANNEL_USERNAME}"
        )
        return

    url = update.message.text.strip()
    
    # تحقق إذا كان الرابط يحتوي على نطاق يوتيوب
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ هذا الرابط ليس رابط يوتيوب صالح")
        return

    await update.message.reply_text("⏳ جاري التحميل، انتظر شوي...")

    try:
        filename = download_video(url)
        await update.message.reply_text("✅ تم التحميل! جاري الإرسال...")

        # إرسال الفيديو مع عرض معلومات عنه
        with open(filename, "rb") as video:
            await update.message.reply_video(
                video,
                caption="🎥 تم التحميل بنجاح!\n\n" +
                       "اشترك في القناة إذا استفدت: @" + CHANNEL_USERNAME[1:]
            )

        # حذف الملف بعد الإرسال
        os.remove(filename)
        logger.info(f"تم حذف الملف: {filename}")

    except Exception as e:
        logger.error(f"خطأ أثناء التحميل: {e}")
        error_msg = str(e)
        if "Private video" in error_msg or "Sign in" in error_msg:
            await update.message.reply_text(
                "🔒 هذا الفيديو خاص أو يتطلب تسجيل الدخول\n\n" +
                "تأكد أن ملف cookies.txt يحتوي على بيانات الجلسة الصحيحة"
            )
        else:
            await update.message.reply_text(f"❌ صار خطأ أثناء التحميل: {error_msg}")

async def cookies_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات عن ملف الكوكيز"""
    if os.path.exists(COOKIES_FILE):
        file_size = os.path.getsize(COOKIES_FILE)
        await update.message.reply_text(
            f"📁 ملف الكوكيز موجود\n"
            f"الحجم: {file_size} bytes\n"
            f"آخر تعديل: {os.path.getmtime(COOKIES_FILE)}"
        )
    else:
        await update.message.reply_text(
            "❌ ملف cookies.txt غير موجود\n\n"
            "لإضافة ملف الكوكيز:\n"
            "1. استخدم إضافة 'Get cookies.txt LOCALLY' في Kiwi\n"
            "2. احفظ الملف في نفس مجلد البوت\n"
            "3. تأكد من تسميته cookies.txt"
        )

# ──────────── تشغيل التطبيق ────────────
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN غير موجود! تأكد أنك خزّنته بالـ GitHub Secrets")

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # التحقق من وجود ملف الكوكيز
    if os.path.exists(COOKIES_FILE):
        logger.info(f"✅ تم العثور على ملف الكوكيز: {COOKIES_FILE}")
    else:
        logger.warning("⚠️ ملف cookies.txt غير موجود - التحميل بدون مصادقة")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cookies", cookies_info))  # أمر جديد للتحقق من الكوكيز
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    logger.info("🚀 البوت بدأ يشتغل...")
    app.run_polling()
