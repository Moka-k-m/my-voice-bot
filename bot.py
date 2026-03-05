import logging
import os
import tempfile
import sys
import asyncio
import signal
import nest_asyncio
import soundfile as sf
import numpy as np
from pydub import AudioSegment

nest_asyncio.apply()

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
    from kittentts import KittenTTS
except ImportError as e:
    print(f"Error: {e}")
    sys.exit(1)

TOKEN = os.environ.get("TOKEN")
RUN_HOURS = int(os.environ.get("RUN_HOURS", 5))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- إعدادات الأصوات (الأسماء الجميلة مقابل الأكواد التقنية) ---
# المفتاح: الاسم اللي هيظهر للمستخدم
# القيمة: الكود اللي المكتبة تفهمه
VOICE_MAP = {
    "Adam (Male)": "expr-voice-2-m",
    "Bella (Female)": "expr-voice-2-f",
    "Charlie (Male)": "expr-voice-3-m",
    "Diana (Female)": "expr-voice-3-f",
    "Ethan (Male)": "expr-voice-4-m",
    "Fiona (Female)": "expr-voice-4-f",
    "George (Male)": "expr-voice-5-m",
    "Hannah (Female)": "expr-voice-5-f"
}

AVAILABLE_VOICES = list(VOICE_MAP.keys())  # الأسماء اللي هتظهر في الأزرار
DEFAULT_VOICE = "Adam (Male)"              # الاسم الافتراضي
SPEED_RATE = 1.2
user_preferences = {}

# --- محرك الصوت ---
class TTSEngine:
    def __init__(self):
        logger.info("Loading TTS Model...")
        self.model = None
        try:
            self.model = KittenTTS()
            logger.info("✅ Model Loaded Successfully.")
        except Exception as e:
            logger.error(f"❌ Model Failed to Load: {e}")

    def generate_audio(self, text: str, voice_code: str, speed: float):
        if not self.model: return None
        temp_wav = tempfile.mktemp(suffix=".wav")
        temp_ogg = tempfile.mktemp(suffix=".ogg")
        try:
            # استخدام الكود التقني في التوليد
            wav_array = self.model.generate(text, voice=voice_code, speed=speed)
            sf.write(temp_wav, wav_array, 24000)
            
            sound = AudioSegment.from_file(temp_wav)
            new_rate = int(sound.frame_rate * speed)
            sound = sound._spawn(sound.raw_data, overrides={"frame_rate": new_rate}).set_frame_rate(sound.frame_rate)
            sound.export(temp_ogg, format="ogg", codec="libopus")
            
            return temp_ogg
        except Exception as e:
            logger.error(f"Generation Error: {e}")
            return None
        finally:
            if os.path.exists(temp_wav): os.remove(temp_wav)

tts_engine = TTSEngine()

# --- دوال البوت ---
def get_voice_keyboard():
    # ترتيب الأزرار في صفين
    keyboard = [
        [InlineKeyboardButton(v, callback_data=f"voice_{v}") for v in AVAILABLE_VOICES[:4]],
        [InlineKeyboardButton(v, callback_data=f"voice_{v}") for v in AVAILABLE_VOICES[4:]]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(u, c): 
    user_preferences[u.effective_user.id] = DEFAULT_VOICE
    await u.message.reply_text(
        f"👋 Bot is Active!\n"
        f"Current Voice: {DEFAULT_VOICE}\n"
        f"Send text to convert.\n"
        f"/voices to change."
    )

async def voices_cmd(u, c): 
    await u.message.reply_text("🎤 Choose a voice:", reply_markup=get_voice_keyboard())

async def voice_cb(u, c):
    q = u.callback_query
    await q.answer()
    data = q.data
    if data.startswith("voice_"):
        selected_voice = data.split("_")[1]
        user_preferences[u.effective_user.id] = selected_voice
        await q.edit_message_text(text=f"✅ Selected: {selected_voice}")

async def text_handler(u, c):
    uid = u.effective_user.id
    txt = u.message.text
    
    # الحصول على الاسم الجميل من تفضيلات المستخدم
    selected_voice_name = user_preferences.get(uid, DEFAULT_VOICE)
    
    # تحويل الاسم الجميل إلى الكود التقني (مثلاً: "Adam..." -> "expr-voice-2-m")
    voice_code = VOICE_MAP.get(selected_voice_name, "expr-voice-2-m")
    
    msg = await u.message.reply_text("⏳ Processing...")
    try:
        audio = tts_engine.generate_audio(txt, voice_code, SPEED_RATE)
        if audio:
            await u.message.reply_voice(open(audio, 'rb'), caption=f"🔊 {selected_voice_name}")
            await msg.delete()
            os.remove(audio)
        else: 
            await msg.edit_text("❌ Error generating audio.")
    except Exception as e:
        logger.error(e)
        await msg.edit_text("❌ Failed.")

# --- نظام التشغيل والتوقف التلقائي ---
def main():
    if not TOKEN:
        logger.error("TOKEN missing in Secrets!")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("voices", voices_cmd))
    app.add_handler(CallbackQueryHandler(voice_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    async def stop_after_timeout(app):
        logger.info(f"Bot scheduled to stop in {RUN_HOURS} hours...")
        await asyncio.sleep(RUN_HOURS * 3600)
        logger.info("Time's up! Stopping bot gracefully...")
        await app.stop()
        await app.shutdown()
        os.kill(os.getpid(), signal.SIGTERM)

    async def run_app():
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        
        asyncio.create_task(stop_after_timeout(app))
        
        logger.info("🚀 Bot is running...")
        while app.running:
            await asyncio.sleep(1)

    try:
        asyncio.run(run_app())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

if __name__ == "__main__":
    main()
