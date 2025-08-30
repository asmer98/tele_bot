import os
import yt_dlp
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 🔑 التوكن من متغير بيئة
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@p_y_hy"
COOKIES_FILE = "cookies.txt"

# 📝 إعدادات الـ logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# قائمة بالمنصات المدعومة (يمكن إضافة المزيد)
SUPPORTED_PLATFORMS = [
    'youtube.com', 'youtu.be',          # يوتيوب
    'twitter.com', 'x.com',             # تويتر/X
    'instagram.com',                    # انستغرام
    'facebook.com', 'fb.watch',         # فيسبوك
    'tiktok.com',                       # تيك توك
    'reddit.com',                       |# ريديت
    'twitch.tv',                        |# تويتش
    'dailymotion.com',                  |# ديلي موشن
    'vimeo.com',                        |# فيمو
    'soundcloud.com',                   |# ساوند كلاود
    'pinterest.com',                    |# بينتريست
    'likee.video',                      |# لايكي
    'rumble.com',                       |# رامبل
    'bilibili.com',                     |# بيلبيل
    'nicovideo.jp',                     |# نيكو نيكو
    'twitcasting.tv',                   |# تويتر كاستينغ
]

# ──────────── الأوامر ────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(update, context):
        await update.message.reply_text(f"⚠️ حتى تقدر تستخدم البوت، اشترك أولًا بالقناة: {CHANNEL_USERNAME}")
        return

    await update.message.reply_text(
        "👋 أهلاً بيك حبيبي في بوت احمد خان أرسل لي رابط الفيديو من أي منصة وأنا أحمله إلك 🎥\n\n"
        "📱 المنصات المدعومة:\n"
        "• يوتيوب YouTube\n"
        "• تويتر Twitter/X\n" 
        "• انستغرام Instagram\n"
        "• فيسبوك Facebook\n"
        "• تيك توك TikTok\n"
        "• ريديت Reddit\n"
        "• والمزيد..."
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

def is_supported_url(url: str) -> bool:
    """يتحقق إذا كان الرابط من منصة مدعومة"""
    import re
    # تحقق من أن الرابط يحتوي على نطاق من المنصات المدعومة
    return any(platform in url for platform in SUPPORTED_PLATFORMS)

def download_video(url: str) -> str:
    """تحميل الفيديو من أي منصة"""
    ydl_opts = {
        "format": "best",  # أفضل جودة متاحة
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        "quiet": True,
        "socket_timeout": 30,
        "retries": 3,
        "noplaylist": True,  # عدم تحميل القوائم
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # تسجيل معلومات المنصة
            platform = info.get('extractor', 'unknown')
            logger.info(f"تم التحميل من {platform}: {info.get('title', 'unknown')}")
            
            return filename
    except Exception as e:
        logger.error(f"خطأ في التحميل: {e}")
        raise Exception(f"خطأ في التحميل: {str(e)}")

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(update, context):
        await update.message.reply_text(f"⚠️ حتى تقدر تستخدم البوت، اشترك أولًا بالقناة: {CHANNEL_USERNAME}")
        return

    url = update.message.text.strip()
    
    # التحقق إذا كان الرابط مدعوم
    if not is_supported_url(url):
        await update.message.reply_text(
            "❌ هذا الرابط غير مدعوم أو غير صحيح\n\n"
            "✅ المنصات المدعومة:\n"
            "• يوتيوب\n• تويتر/X\n• انستغرام\n• فيسبوك\n"
            "• تيك توك\n• ريديت\n• تويتش\n• وغيرها\n\n"
            "🔗 مثال: https://www.youtube.com/watch?v=..."
        )
        return

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
            await update.message.reply_text("🔒 هذا المحتوى خاص أو يتطلب تسجيل دخول")
        elif "Unsupported" in error_msg:
            await update.message.reply_text("❌ هذه المنصة غير مدعومة حالياً")
        else:
            await update.message.reply_text(f"❌ صار خطأ أثناء التحميل: {error_msg}")

async def cookies_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات عن ملف الكوكيز"""
    if os.path.exists(COOKIES_FILE):
        file_size = os.path.getsize(COOKIES_FILE)
        await update.message.reply_text(f"📁 ملف الكوكيز موجود\nالحجم: {file_size} bytes")
    else:
        await update.message.reply_text("❌ ملف cookies.txt غير موجود")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رسالة المساعدة"""
    await update.message.reply_text(
        "📖 أوامر البوت:\n\n"
        "/start - بدء استخدام البوت\n"
        "/help - عرض هذه الرسالة\n"
        "/cookies - معلومات عن ملف الكوكيز\n\n"
        "📱 فقط أرسل رابط الفيديو وسأحمله لك!"
    )

# ──────────── تشغيل التطبيق ────────────
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN غير موجود! تأكد أنك خزّنته بالـ GitHub Secrets")

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cookies", cookies_info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    logger.info("🚀 البوت بدأ يشتغل...")
    app.run_polling()
