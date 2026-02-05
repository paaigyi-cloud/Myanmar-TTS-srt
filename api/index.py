from http.server import BaseHTTPRequestHandler
import json
import asyncio
import edge_tts
import re
import base64

# --- Helper Functions ---
def apply_pronunciation_rules(text, rules_str):
    if not rules_str: return text
    for line in rules_str.split('\n'):
        if '=' in line:
            k, v = line.split('=')
            text = text.replace(k.strip(), v.strip())
    return text

def split_text(text):
    # Split by punctuation but keep delimiters
    parts = re.split(r'([!။.;!?၊])', text)
    segments = []
    current = ""
    for p in parts:
        if p in ['။', '.', '!', ';', '?', '၊']:
            if current:
                segments.append((current + p).strip())
                current = ""
            elif segments:
                segments[-1] += p
        else:
            current += p
    if current.strip(): segments.append(current.strip())
    return segments

def format_srt_time(seconds):
    millis = int((seconds - int(seconds)) * 1000)
    s = int(seconds)
    m = s // 60
    h = m // 60
    return f"{h:02}:{m%60:02}:{s%60:02},{millis:03}"

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
            platform = data.get('platform', 'TikTok')

            # Voice Map
            if "Female" in voice or "Nilar" in voice: voice = "my-MM-NilarNeural"
            elif "Ryan" in voice: voice = "en-GB-RyanNeural"
            elif "Sonia" in voice: voice = "en-GB-SoniaNeural"
            else: voice = "my-MM-ThihaNeural"

            rate_str = f"{int(speed):+d}%"
            pitch_str = f"{int(pitch) * -1:+d}Hz"
            
            clean_text = text.replace('\n', ' ')
            segments = apply_pronunciation_rules(clean_text, rules)
            segments = split_text(segments)
            
            final_audio = b""
            srt_content = ""
            srt_index = 1
            current_time = 0.0
            srt_limit = 150 if "YouTube" in platform else 55

            async def generate():
                nonlocal final_audio, srt_content, srt_index, current_time
                for seg in segments:
                    if not seg.strip(): continue
                    
                    # Generate Audio
                    comm = edge_tts.Communicate(seg, voice, rate=rate_str, pitch=pitch_str)
                    seg_audio = b""
                    async for chunk in comm.stream():
                        if chunk["type"] == "audio":
                            seg_audio += chunk["data"]
                    
                    final_audio += seg_audio
                    
                    # Simple SRT Estimation (1 char ~ 0.1s approx for speed calculation)
                    # Adjust based on audio length if possible, but simple ratio is safer for Vercel timeout
                    # Estimate duration based on bytes: 24khz mono mp3 is roughly 3-4kb/s (varies)
                    # Let's use character count ratio for sync within the segment
                    est_duration = len(seg) * 0.15 # Rough guess
                    
                    # Create SRT chunks
                    words = seg.split(' ')
                    current_srt_chunk = ""
                    chunk_start = current_time
                    
                    chunks_list = []
                    curr = ""
                    for w in words:
                        if len(curr) + len(w) < srt_limit: curr += w + " "
                        else: 
                            chunks_list.append(curr.strip())
                            curr = w + " "
                    if curr.strip(): chunks_list.append(curr.strip())

                    seg_duration = est_duration 
                    # If we could get exact duration from edge-tts metadata it would be better, 
                    # but simple estimation works for short clips.
                    
                    for i, chunk in enumerate(chunks_list):
                        chunk_dur = (len(chunk) / len(seg)) * seg_duration
                        if chunk_dur < 0.5: chunk_dur = 0.5
                        
                        start_fmt = format_srt_time(chunk_start)
                        end_fmt = format_srt_time(chunk_start + chunk_dur)
                        srt_content += f"{srt_index}\n{start_fmt} --> {end_fmt}\n{chunk}\n\n"
                        
                        srt_index += 1
                        chunk_start += chunk_dur
                    
                    current_time += seg_duration

            asyncio.run(generate())

            # Respond
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
