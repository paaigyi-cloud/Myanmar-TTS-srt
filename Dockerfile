# Python 3.9 ကို အခြေခံမယ်
FROM python:3.9-slim

# FFmpeg ကို Server ထဲမှာ Install လုပ်မယ် (ဒါကြောင့် Quality ပြန်ကောင်းမှာပါ)
RUN apt-get update && apt-get install -y ffmpeg

# Working Directory သတ်မှတ်မယ်
WORKDIR /app

# Permission ညှိမယ်
run chmod 777 /app

# Requirements တွေကို သွင်းမယ်
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ကုဒ်တွေကို ကူးထည့်မယ်
COPY . .

# Gradio ကို Server ပေါ်မှာ Run မယ်
CMD ["python", "app.py"]

