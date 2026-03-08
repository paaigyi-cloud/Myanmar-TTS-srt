import gradio as gr
import os

with gr.Blocks() as demo:
    gr.Markdown(
        """
        <div style="text-align: center; padding: 50px;">
            <h1 style="color: #ff4b4b;">⚠️ အသိပေးအကြောင်းကြားချက်</h1>
            <br>
            <h3 style="line-height: 1.8; color: #333;">
                အသုံးပြုသူများလာသောကြောင့် Server မနိုင်တော့ပါသဖြင့်<br>
                Telegram သို့ ဝင်ရောက်အသုံးပြုပေးကြပါရန် မေတ္တာရပ်ခံပါသည်။
            </h3>
            <br><br>
            <a href="https://t.me/+j9i087I30oMyZTdl" target="_blank" style="background-color: #0088cc; color: white; padding: 20px 40px; text-decoration: none; border-radius: 10px; font-size: 20px; font-weight: bold; box-shadow: 0 4px 15px rgba(0,136,204,0.3);">
                👉 Telegram Group သို့ ဝင်ရောက်ရန် ဤနေရာကို နှိပ်ပါ
            </a>
        </div>
        """
    )

if __name__ == "__main__":
    # Render ရဲ့ Port စနစ်နဲ့ ကိုက်ညီအောင် ပြင်ဆင်ထားခြင်း
    server_port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=server_port)
