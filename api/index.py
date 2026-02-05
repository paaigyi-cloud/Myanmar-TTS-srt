from http.server import BaseHTTPRequestHandler
import json
import asyncio
import edge_tts
from edge_tts import SubMaker # SRT အတွက် ဒါလေး အသစ်ပါလာပါမယ်
import base64

# --- Helper: Pronunciation Fixer ---
def apply_pronunciation_rules(text, rules_str):
    if not rules_str: return text
    for line in rules_str.split('\n'):
        if '=' in line:
            parts = line.split('=')
            if len(parts) >= 2:
                k = parts[0].strip()
                v = parts[1].strip()
                if k and v:
                    text = text.replace(k, v)
    return text

# --- Main Handler ---
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            text = data.get('text', '')
            rules = data.get('rules', '')
            voice = data.get('voice', 'my-MM-ThihaNeural')
            speed = data.get('speed', '0')
            pitch = data.get('pitch', '0')

            if not text.strip():
                self.send_response(400)
                self.end_headers()
                return

            # Voice Map
            if "Female" in voice or "Nilar" in voice: voice = "my-MM-NilarNeural"
            elif "Ryan" in voice: voice = "en-GB-RyanNeural"
            elif "Sonia" in voice: voice = "en-GB-SoniaNeural"
            else: voice = "my-MM-ThihaNeural"

            rate_str = f"{int(speed):+d}%"
            pitch_str = f"{int(pitch) * -1:+d}Hz"
            
            # ၁။ Rules တွေ အရင်ရှင်းမယ်
            clean_text = apply_pronunciation_rules(text, rules)
            # Newlines တွေကို space ပြောင်းမယ် (အသံမရပ်သွားအောင်)
            clean_text = clean_text.replace('\n', ' ')

            final_audio = b""
            srt_content = ""

            # ၂။ တောက်လျှောက် အသံထုတ်မယ် (Continuous Generation)
            async def generate():
                nonlocal final_audio, srt_content
                
                communicate = edge_tts.Communicate(clean_text, voice, rate=rate_str, pitch=pitch_str)
                submaker = SubMaker() # SRT ဖန်တီးသူ
                
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        final_audio += chunk["data"]
                    elif chunk["type"] == "WordBoundary":
                        # စာလုံးတစ်လုံးချင်းစီရဲ့ အချိန်ကို မှတ်မယ်
                        submaker.feed(chunk)
                
                # ၃။ SRT ကို Auto ထုတ်ယူမယ်
                srt_content = submaker.get_srt()

            asyncio.run(generate())

            # ၄။ ပြန်ပို့မယ်
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = json.dumps({
                'audio': base64.b64encode(final_audio).decode('utf-8'),
                'srt': srt_content
            })
            self.wfile.write(response.encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
