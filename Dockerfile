FROM python:3.10-slim

# تثبيت النظام ومكتبات الصوت
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# تعيين مجلد العمل
WORKDIR /app

# نسخ ملف المتطلبات وتثبيتهم
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الملفات
COPY . .

# أمر التشغيل
CMD ["python", "app.py"]
