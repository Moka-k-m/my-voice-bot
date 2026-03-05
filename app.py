import os
import soundfile as sf
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from kittentts import KittenTTS

# 1. التوكن بتاعك 🔑
TOKEN = "8798797433:AAHAbBMPIuihteiiwHEfch80bUu6uSPZ38g"

# 2. استدعاء القطة 🐈
print("جاري شحن حنجرة القطة... 🐾")
# ملحوظة: التحميل بيتم من Hugging Face Hub تلقائياً
model = KittenTTS("KittenML/kitten-tts-mini-0.8")

VOICES = ['Bella', 'Hugo', 'Leo', 'Kiki', 'Luna', 'Rosie']

# --- الوظائف البرمجية ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"يا أهلاً بك يا {user.first_name}! 🐾\nأنا قطتك الناطقة. اكتب لي أي نص بالإنجليزية وسأنطقه لك.\nأو استخدم /voice لتغيير الشخصية.")

async def voice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(v, callback_data=v)] for v in VOICES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("اختر الحنجرة التي تفضلها اليوم: 🎙️", reply_markup=reply_markup)

async def select_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['voice'] = query.data
    await query.edit_message_text(f"تم اختيار الصوت: {query.data} ✅.. القطة جاهزة!")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    selected_voice = context.user_data.get('voice', 'Bella')
    
    await update.message.reply_text(f"جاري تحويل النص لصوت {selected_voice}... 🎤")
    
    try:
        # توليد الصوت
        wav = model.generate(text, voice=selected_voice, speed=1.3)
        sf.write('temp.wav', wav, 24000)
        
        # تحويل الملف باستخدام ffmpeg (لازم يكون مثبت في الـ Docker)
        os.system("ffmpeg -i temp.wav -c:a libopus voice.ogg -y")
        
        with open('voice.ogg', 'rb') as v:
            await update.message.reply_voice(voice=v)
    except Exception as e:
        await update.message.reply_text(f"حصلت مشكلة يا صديقي: {e} 🙀")

if __name__ == '__main__':
    print("البوت بدأ العمل.. روح كلمه على تليجرام! 🚀")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("voice", voice_menu))
    app.add_handler(CallbackQueryHandler(select_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    app.run_polling()