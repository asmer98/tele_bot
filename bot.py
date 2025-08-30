import os
import yt_dlp
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 🔑 التوكن من متغير بيئة
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@p_y_hy"
COOKIES_FILE = "cookies.txt"  # ملف كوكيز واحد لجميع المنصات

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
        "👋 أهلاً بيك في بوت احمد خان أرسل لي رابط الفيديو من أي منصة وأنا أحمله إلك 🎥"
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
        "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        "quiet": True,
        "socket_timeout": 30,
        "retries": 3,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
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
        await update.message.reply_text(f"❌ صار خطأ أثناء التحميل: {error_msg}")

async def cookies_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات عن ملف الكوكيز"""
    if os.path.exists(COOKIES_FILE):
        file_size = os.path.getsize(COOKIES_FILE)
        await update.message.reply_text(f"📁 ملف الكوكيز موجود\nالحجم: {file_size} bytes")
    else:
        await update.message.reply_text("❌ ملف cookies.txt غير موجود")

# ──────────── تشغيل التطبيق ────────────
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN غير موجود! تأكد أنك خزّنته بالـ GitHub Secrets")

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cookies", cookies_info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    logger.info("🚀 البوت بدأ يشتغل...")
    app.run_polling()
