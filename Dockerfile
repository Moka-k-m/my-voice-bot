# إجبار استخدام بايثون 3.10
FROM python:3.10-slim

# تحديث النظام وتثبيت المحركات الصوتية
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak-ng \
    git \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# تثبيت المكتبات الأساسية "عافية"
RUN pip install --no-cache-dir numpy==1.26.4 soundfile librosa python-telegram-bot==20.8

# تثبيت misaki بنسخة قديمة متوافقة
RUN pip install --no-cache-dir "misaki==0.7.4"

# تثبيت القطة بدون ما يراجع وراها (No Dependencies)
RUN pip install --no-cache-dir --no-deps https://github.com/KittenML/KittenTTS/releases/download/0.8/kittentts-0.8.0-py3-none-any.whl

# تثبيت الحاجات اللي ناقصة عشان القطة تموء
RUN pip install --no-cache-dir phonemizer num2words spacy espeakng_loader onnxruntime scipy

# نسخ الكود
COPY . .

# تشغيل البوت
CMD ["python", "app.py"]