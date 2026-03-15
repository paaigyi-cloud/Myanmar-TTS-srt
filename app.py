from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import os

app = FastAPI()

# UptimeRobot မှ လာသော မတူညီသည့် HTTP Method များကို လက်ခံနိုင်ရန် api_route ကို ပြောင်းလဲအသုံးပြုထားပါသည်
@app.api_route("/", methods=["GET", "HEAD", "POST", "OPTIONS"], response_class=HTMLResponse)
def read_root():
    return """
    <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Myanmar TTS Notification</title>
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f4f7f6; }
                .container { text-align: center; padding: 40px; background: white; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); max-width: 500px; margin: 20px; }
                h1 { color: #ff4b4b; margin-bottom: 20px; }
                h3 { line-height: 1.8; color: #333; margin-bottom: 30px; }
                .btn { background-color: #0088cc; color: white; padding: 18px 35px; text-decoration: none; border-radius: 10px; font-size: 18px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(0,136,204,0.3); }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚠️ အသိပေးချက်</h1>
                <h3>အသုံးပြုသူများလာသောကြောင့် Server မနိုင်တော့ပါသဖြင့်<br>Telegram သို့ ဝင်ရောက်အသုံးပြုပေးကြပါရန် မေတ္တာရပ်ခံအပ်ပါသည်။</h3>
                <a href="https://t.me/+j9i087I30oMyZTdl" class="btn">👉 Telegram Group သို့ ဝင်ရန်</a>
            </div>
        </body>
    </html>
    """

if __name__ == "__main__":
    # Render ၏ Port Binding ပြဿနာကို ဖြေရှင်းရန်
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
