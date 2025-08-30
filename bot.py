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
    """تحميل الفيديو بإعدادات خاصة ل GitHub Actions"""
    ydl_opts = {
        # الإعدادات الأساسية
        "format": "bestvideo+bestaudio/best",
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "merge_output_format": "mp4",
        "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        
        # 🔥 الإعدادات الحاسمة لحل المشكلة:
        "verbose": True,
        "no_warnings": False,
        "ignoreerrors": False,
        
        # إعدادات الشبكة المهمة
        "socket_timeout": 120,
        "retries": 10,
        "fragment_retries": 10,
        "skip_unavailable_fragments": True,
        "continue_dl": True,
        
        # ⚡ إعدادات يوتيوب المحددة
        "extract_flat": False,
        "live_from_start": True,
        "wait_for_video": (5, 60),
        
        # 🌐 إعدادات User-Agent للتحايل على الحجب
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-us,en;q=0.5",
            "Accept-Encoding": "gzip,deflate",
            "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.7",
            "Connection": "keep-alive",
        },
        
        # إعدادات الأداء
        "concurrent_fragment_downloads": 3,
        "buffersize": 1024 * 1024,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # تحميل المعلومات أولاً
            info = ydl.extract_info(url, download=False)
            logger.info(f"⏳ جاري تحميل: {info.get('title', 'unknown')}")
            
            # التحميل الفعلي
            ydl.download([url])
            
            filename = ydl.prepare_filename(info)
            return filename
            
    except Exception as e:
        logger.error(f"خطأ في التحميل: {e}", exc_info=True)
        raise Exception(f"فشل التحميل: {str(e)}")
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
