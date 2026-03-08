import gradio as gr

with gr.Blocks() as demo:
    gr.Markdown(
        """
        <div style="text-align: center; padding: 50px;">
            <h1>⚠️ အသိပေးအကြောင်းကြားချက်</h1>
            <br>
            <h3 style="line-height: 1.8;">
                အသုံးပြုသူများလာသောကြောင့် Server မနိုင်တော့ပါသဖြင့်<br>
                Telegram သို့ ဝင်ရောက်အသုံးပြုပေးကြပါရန် မေတ္တာရပ်ခံပါသည်။
            </h3>
            <br><br>
            <a href="https://t.me/+j9i087I30oMyZTdl" target="_blank" style="background-color: #0088cc; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-size: 18px; font-weight: bold;">
                👉 Telegram Group သို့ ဝင်ရောက်ရန် ဤနေရာကို နှိပ်ပါ
            </a>
        </div>
        """
    )

demo.launch()
