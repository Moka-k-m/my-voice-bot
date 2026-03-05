import logging
import os
import tempfile
import sys
import asyncio
import time
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
# متغير لتحديد وقت التشغيل (بالساعات) - افتراضياً 5 ساعات
RUN_HOURS = int(os.environ.get("RUN_HOURS", 5))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

AVAILABLE_VOICES = ["expr-voice-2-m", "expr-voice-2-f", "expr-voice-3-m", "expr-voice-3-f", "expr-voice-4-m", "expr-voice-4-f", "expr-voice-5-m", "expr-voice-5-f"]
DEFAULT_VOICE = "expr-voice-2-m"
SPEED_RATE = 1.2
user_preferences = {}

class TTSEngine:
    def __init__(self):
        logger.info("Loading Model...")
        self.model = None
        try:
            self.model = KittenTTS()
            logger.info("Model Loaded.")
        except Exception as e:
            logger.error(f"Model Fail: {e}")

    def generate_audio(self, text: str, voice: str, speed: float):
        if not self.model: return None
        temp_wav = tempfile.mktemp(suffix=".wav")
        temp_ogg = tempfile.mktemp(suffix=".ogg")
        try:
            wav_array = self.model.generate(text, voice=voice, speed=speed)
            sf.write(temp_wav, wav_array, 24000)
            sound = AudioSegment.from_file(temp_wav)
            new_rate = int(sound.frame_rate * speed)
            sound = sound._spawn(sound.raw_data, overrides={"frame_rate": new_rate}).set_frame_rate(sound.frame_rate)
            sound.export(temp_ogg, format="ogg", codec="libopus")
            return temp_ogg
        except Exception as e:
            logger.error(e)
            return None
        finally:
            if os.path.exists(temp_wav): os.remove(temp_wav)

tts_engine = TTSEngine()

def get_voice_keyboard():
    keyboard = [[InlineKeyboardButton(v, callback_data=f"voice_{v}") for v in AVAILABLE_VOICES[:4]],
                [InlineKeyboardButton(v, callback_data=f"voice_{v}") for v in AVAILABLE_VOICES[4:]]]
    return InlineKeyboardMarkup(keyboard)

async def start(u, c): 
    user_preferences[u.effective_user.id] = DEFAULT_VOICE
    await u.message.reply_text(f"👋 Bot Active (GitHub Action Mode)!\nVoice: {DEFAULT_VOICE}\n/voices to change.")

async def voices_cmd(u, c): await u.message.reply_text("🎤 Choose:", reply_markup=get_voice_keyboard())

async def voice_cb(u, c):
    q = u.callback_query
    await q.answer()
    v = q.data.split("_")[1]
    user_preferences[u.effective_user.id] = v
    await q.edit_message_text(f"✅ Selected: {v}")

async def text_handler(u, c):
    uid = u.effective_user.id
    txt = u.message.text
    v = user_preferences.get(uid, DEFAULT_VOICE)
    msg = await u.message.reply_text("⏳ Processing...")
    try:
        audio = tts_engine.generate_audio(txt, v, SPEED_RATE)
        if audio:
            await u.message.reply_voice(open(audio, 'rb'), caption=f"🔊 {v}")
            await msg.delete()
            os.remove(audio)
        else: await msg.edit_text("❌ Error.")
    except Exception as e:
        await msg.edit_text("❌ Failed.")

def main():
    if not TOKEN:
        logger.error("TOKEN missing!")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("voices", voices_cmd))
    app.add_handler(CallbackQueryHandler(voice_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    # --- نظام التوقف التلقائي (Auto Stop) ---
    async def stop_after_timeout(app):
        logger.info(f"Bot will stop in {RUN_HOURS} hours...")
        await asyncio.sleep(RUN_HOURS * 3600)
        logger.info("Time's up! Stopping bot gracefully...")
        await app.stop()
        await app.shutdown()
        # قتل العملية تماماً لإنهاء الـ Workflow
        os.kill(os.getpid(), signal.SIGTERM)

    async def run_app():
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        
        # تشغيل مهمة التوقف في الخلفية
        asyncio.create_task(stop_after_timeout(app))
        
        logger.info("Bot is running...")
        while app.running:
            await asyncio.sleep(1)

    try:
        asyncio.run(run_app())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

if __name__ == "__main__":
    main()
