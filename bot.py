import os
import yt_dlp
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 🔑 التوكن من متغير بيئة
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@p_y_hy"

# 📝 إعدادات الـ logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ──────────── الأوامر ────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بيك انا بوت احمد خان أرسل لي رابط الفيديو وأنا أحمله إلك 🎥")

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not url.startswith('http'):
        await update.message.reply_text("❌ هذا ليس رابط صحيح")
        return

    await update.message.reply_text("⏳ جاري التحميل، انتظر شوي...")

    try:
        # إعدادات بسيطة بدون تعقيد
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        await update.message.reply_text("✅ تم التحميل! جاري الإرسال...")

        with open(filename, 'rb') as video:
            await update.message.reply_video(video)

        os.remove(filename)

    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في التحميل: {str(e)}")

# ──────────── تشغيل التطبيق ────────────
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN غير موجود!")

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    logger.info("🚀 البوت بدأ يشتغل...")
    app.run_polling()
