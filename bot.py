import os
import yt_dlp
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 🔑 التوكن من متغير بيئة
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@p_y_hy"

# 📁 ملفات الكوكيز للمنصات المختلفة
YOUTUBE_COOKIES = "cookies_youtube.txt"
INSTAGRAM_COOKIES = "cookies_instagram.txt"
DEFAULT_COOKIES = "cookies.txt"

# 📝 إعدادات الـ logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ──────────── الأوامر ────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(update, context):
        await update.message.reply_text(f"⚠️ حتى تقدر تستخدم البوت، اشترك أولًا بالقناة: {CHANNEL_USERNAME}")
        return

    await update.message.reply_text(
        "👋 أهلاً بيك في بوت احمد خان أرسل لي رابط الفيديو من أي منصة وأنا أحمله إلك 🎥\n\n"
        "📱 المنصات المدعومة:\n"
        "• يوتيوب YouTube\n• تويتر/X\n• انستغرام Instagram\n"
        "• فيسبوك Facebook\n• تيك توك TikTok\n• ريديت Reddit\n"
        "• تويتش Twitch\n• وغيرها الكثير...\n\n"
        "🔐 للمحتوى الخاص: تأكد من وجود ملفات الكوكيز"
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

def get_cookies_file(url: str) -> str:
    """إرجاع ملف الكوكيز المناسب للمنصة"""
    if 'instagram.com' in url and os.path.exists(INSTAGRAM_COOKIES):
        return INSTAGRAM_COOKIES
    elif ('youtube.com' in url or 'youtu.be' in url) and os.path.exists(YOUTUBE_COOKIES):
        return YOUTUBE_COOKIES
    elif os.path.exists(DEFAULT_COOKIES):
        return DEFAULT_COOKIES
    else:
        return None

def download_video(url: str) -> str:
    """تحميل الفيديو وإرجاع المسار"""
    cookies_file = get_cookies_file(url)
    
    ydl_opts = {
        "format": "best",
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "cookiefile": cookies_file,
        "quiet": True,
        "noplaylist": True,
    }
    
    # إعدادات خاصة للانستقرام
    if 'instagram.com' in url:
        ydl_opts.update({
            "socket_timeout": 120,
            "retries": 10,
            "fragment_retries": 10,
            "extract_flat": False,
            "wait_for_video": (5, 30),
            "concurrent_fragment_downloads": 2,
        })
    
    # إعدادات خاصة لليوتيوب
    elif 'youtube.com' in url or 'youtu.be' in url:
        ydl_opts.update({
            "socket_timeout": 60,
            "retries": 5,
            "fragment_retries": 5,
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # تسجيل معلومات المنصة المستخدمة
            platform = "انستقرام" if 'instagram.com' in url else "يوتيوب" if 'youtube.com' in url else "منصة أخرى"
            logger.info(f"تم التحميل من {platform} باستخدام: {cookies_file}")
            
            return filename
    except Exception as e:
        logger.error(f"خطأ في التحميل: {e}")
        raise Exception(f"خطأ في التحميل: {str(e)}")

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(update, context):
        await update.message.reply_text(f"⚠️ حتى تقدر تستخدم البوت، اشترك أولًا بالقناة: {CHANNEL_USERNAME}")
        return

    url = update.message.text.strip()
    await update.message.reply_text("⏳ جاري التحميل، انتظر شوي...")

    try:
        filename = await asyncio.to_thread(download_video, url)
        
        await update.message.reply_text("✅ تم التحميل! جاري الإرسال...")

        with open(filename, "rb") as video:
            await update.message.reply_video(
                video,
                caption="🎥 تم التحميل بنجاح!\n\nاشترك في القناة إذا استفدت: @" + CHANNEL_USERNAME[1:]
            )

        os.remove(filename)
        logger.info(f"تم حذف الملف: {filename}")

    except Exception as e:
        logger.error(f"خطأ أثناء التحميل: {e}")
        error_msg = str(e)
        
        if "Private" in error_msg or "Sign in" in error_msg:
            platform = "انستقرام" if 'instagram.com' in url else "يوتيوب" if 'youtube.com' in url else "المنصة"
            await update.message.reply_text(
                f"🔒 هذا المحتوى خاص أو يتطلب تسجيل دخول على {platform}\n\n"
                f"تأكد من وجود ملف الكوكيز المناسب"
            )
        elif "Unsupported" in error_msg:
            await update.message.reply_text("❌ هذه المنصة غير مدعومة حالياً")
        else:
            await update.message.reply_text(f"❌ صار خطأ أثناء التحميل: {error_msg}")

async def cookies_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات عن ملفات الكوكيز"""
    message = "📁 معلومات ملفات الكوكيز:\n\n"
    
    files = {
        "يوتيوب": YOUTUBE_COOKIES,
        "انستقرام": INSTAGRAM_COOKIES,
        "افتراضي": DEFAULT_COOKIES
    }
    
    for platform, file_path in files.items():
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            message += f"✅ {platform}: {file_path} ({file_size} bytes)\n"
        else:
            message += f"❌ {platform}: غير موجود\n"
    
    message += "\n📝 لإنشاء ملفات الكوكيز:\n"
    message += "1. استخدم إضافة 'Get cookies.txt LOCALLY' في Kiwi\n"
    message += "2. احفظ الملف باسم المنصة المناسب\n"
    message += "3. تأكد من أنك مسجل دخول في الموقع"
    
    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رسالة المساعدة"""
    await update.message.reply_text(
        "📖 أوامر البوت:\n\n"
        "/start - بدء استخدام البوت\n"
        "/help - عرض هذه الرسالة\n"
        "/cookies - معلومات عن ملفات الكوكيز\n\n"
        "🔐 للمحتوى الخاص:\n"
        "• cookies_youtube.txt - لليوتيوب\n"
        "• cookies_instagram.txt - للانستقرام\n"
        "• cookies.txt - للمنصات الأخرى\n\n"
        "📱 فقط أرسل رابط الفيديو وسأحمله لك!"
    )

# ──────────── تشغيل التطبيق ────────────
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN غير موجود! تأكد أنك خزّنته بالـ GitHub Secrets")

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # التحقق من وجود ملفات الكوكيز
    cookies_files = [YOUTUBE_COOKIES, INSTAGRAM_COOKIES, DEFAULT_COOKIES]
    for file_path in cookies_files:
        if os.path.exists(file_path):
            logger.info(f"✅ تم العثور على ملف الكوكيز: {file_path}")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cookies", cookies_info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    logger.info("🚀 البوت بدأ يشتغل...")
    app.run_polling()
