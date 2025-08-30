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
    """تحميل الفيديو بإعدادات بديلة"""
    import subprocess
    import random
    
    # إنشاء اسم ملف عشوائي لمنع التعارض
    random_id = random.randint(1000, 9999)
    output_template = f"downloads/video_{random_id}.%(ext)s"
    
    # بناء أمر yt-dlp يدويًا
    cmd = [
        "yt-dlp",
        "-f", "best[height<=720]",  # دقة متوسطة لزيادة النجاح
        "--no-part",
        "--socket-timeout", "30",
        "--retries", "5",
        "--fragment-retries", "5",
        "--output", output_template,
    ]
    
    # إضافة الكوكيز إذا موجود
    if os.path.exists(COOKIES_FILE):
        cmd.extend(["--cookies", COOKIES_FILE])
    
    # إضافة الرابط
    cmd.append(url)
    
    try:
        # تنفيذ الأمر مباشرة
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"خطأ في الأمر: {result.stderr}")
            raise Exception(f"فشل التنفيذ: {result.stderr}")
        
        # البحث عن الملف المحمل
        download_dir = "downloads"
        for file in os.listdir(download_dir):
            if file.startswith(f"video_{random_id}"):
                return os.path.join(download_dir, file)
        
        raise Exception("لم يتم العثور على الملف بعد التحميل")
        
    except subprocess.TimeoutExpired:
        logger.error("انتهى وقت التحميل")
        raise Exception("التحميل أخذ وقت طويل جداً")
    except Exception as e:
        logger.error(f"خطأ في التحميل: {e}")
        raise

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
