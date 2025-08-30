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
    """بديل طارئ للتحميل"""
    import requests
    import re
    from urllib.parse import quote
    
    try:
        # استخراج ID الفيديو
        video_id = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        if not video_id:
            raise Exception("رابط يوتيوب غير صحيح")
        
        video_id = video_id.group(1)
        
        # تحميل من موقع بديل
        alt_url = f"https://yt1s.com/api/ajaxSearch/index"
        payload = {
            'q': f"https://www.youtube.com/watch?v={video_id}",
            'vt': 'home'
        }
        
        response = requests.post(alt_url, data=payload)
        data = response.json()
        
        if 'vid' not in data:
            raise Exception("فشل في الحصول على رابط التحميل")
        
        # الحصول على رابط التحميل
        download_url = f"https://yt1s.com/api/ajaxConvert/convert"
        download_payload = {
            'vid': data['vid'],
            'k': data['links']['mp4']['auto']['k']
        }
        
        dl_response = requests.post(download_url, data=download_payload)
        dl_data = dl_response.json()
        
        if 'dlink' not in dl_data:
            raise Exception("فشل في التحويل")
        
        # تحميل الفيديو
        video_url = dl_data['dlink']
        filename = f"downloads/video_{video_id}.mp4"
        
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        return filename
        
    except Exception as e:
        logger.error(f"التحميل الطارئ فشل: {e}")
        raise Exception(f"فشل التحميل: {str(e)}")

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
