import gradio as gr
import edge_tts
import asyncio
import tempfile
import os
from pydub import AudioSegment
import re
import datetime

# --- Global Variables ---
SESSION_COUNT = 0
TOTAL_SECONDS = 0.0 # စုစုပေါင်း ကြာချိန်ကို စက္ကန့်နဲ့ မှတ်ပါမယ်

# --- Setup ---
VOICES = [
    ("အကိုလေး (Male)", "my-MM-ThihaNeural"),
    ("မြမြ (Female)", "my-MM-NilarNeural"),
    ("English UK (Female)", "en-GB-SoniaNeural"),
    ("English UK (Male)", "en-GB-RyanNeural")
]

DEFAULT_RULES = """
မေတ္တာ = မြစ်တာ
သစ္စာ = သစ်စာ
ပြဿနာ = ပြတ်သနာ
ဥစ္စာ = အုတ်စာ
ဦးနှောက် = အုံးနှောက်
"""

# --- Helper Functions ---
def remove_silence_from_end(audio_chunk, silence_thresh=-40.0, chunk_size=10):
    try:
        reversed_audio = audio_chunk.reverse()
        trim_ms = 0
        while trim_ms < len(reversed_audio):
            chunk = reversed_audio[trim_ms:trim_ms+chunk_size]
            if chunk.dBFS > silence_thresh:
                break
            trim_ms += chunk_size
        return reversed_audio[trim_ms:].reverse() if trim_ms < len(reversed_audio) else audio_chunk
    except Exception as e:
        print(f"Silence removal error: {e}")
        return audio_chunk

def format_srt_time(seconds):
    millis = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    minutes = seconds // 60
    hours = minutes // 60
    minutes %= 60
    seconds %= 60
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

def format_duration_display(total_seconds):
    # စက္ကန့်စုစုပေါင်းကို "၀၁ မိနစ် ၃၀ စက္ကန့်" ပုံစံပြောင်းနည်း
    total_seconds = int(total_seconds)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02} မိနစ် {seconds:02} စက္ကန့်"

def apply_pronunciation_rules(text, rules_str):
    if not rules_str: return text
    for line in rules_str.split('\n'):
        if '=' in line:
            parts = line.split('=')
            if len(parts) >= 2:
                text = text.replace(parts[0].strip(), parts[1].strip())
    return text

def split_by_punctuation(text):
    raw_segments = re.split(r'([!။.;!?၊])', text)
    refined_segments = []
    current_text = ""
    for seg in raw_segments:
        if not seg: continue
        if seg in ['။', '.', '!', ';', '?', '၊']:
            if current_text:
                current_text += seg
                refined_segments.append(current_text.strip())
                current_text = ""
            elif refined_segments:
                refined_segments[-1] += seg
        else:
            current_text += seg
    if current_text.strip(): refined_segments.append(current_text.strip())
    return refined_segments

def smart_split_text_for_srt(text, max_chars):
    words = text.split(' ')
    segments = []
    current = ""
    for word in words:
        if len(current) + len(word) < max_chars:
            current += word + " "
        else:
            if current.strip(): segments.append(current.strip())
            current = word + " "
    if current.strip(): segments.append(current.strip())
    return segments

async def generate_precise_audio(text, pronunciation_rules, voice_key, rate_str, pitch_str, volume_boost, max_srt_chars):
    combined_audio = AudioSegment.empty()
    srt_content = ""
    current_audio_time = 0.0
    subtitle_index = 1
    
    text = text.replace("\n", " ")
    audio_segments = split_by_punctuation(text)
    
    temp_dir = tempfile.mkdtemp()
    
    for i, audio_text_segment in enumerate(audio_segments):
        if not audio_text_segment.strip(): continue
        
        speakable_text = apply_pronunciation_rules(audio_text_segment.strip(), pronunciation_rules)
        temp_fname = os.path.join(temp_dir, f"part_{i}.mp3")
        
        try:
            communicate = edge_tts.Communicate(speakable_text, voice_key, rate=rate_str, pitch=pitch_str)
            await communicate.save(temp_fname)
            
            audio_segment = AudioSegment.from_mp3(temp_fname)
            audio_segment = remove_silence_from_end(audio_segment)
            
            segment_duration = len(audio_segment) / 1000.0
            combined_audio += audio_segment
            combined_audio += AudioSegment.silent(duration=50)

            srt_chunks = smart_split_text_for_srt(audio_text_segment, max_chars=max_srt_chars)
            total_chars = len(audio_text_segment) or 1
            segment_start_time = current_audio_time
            
            for chunk in srt_chunks:
                chunk_len = len(chunk)
                chunk_duration = (chunk_len / total_chars) * segment_duration
                if chunk_duration < 0.5 and len(srt_chunks) > 1: chunk_duration = 0.5 

                start_srt = format_srt_time(segment_start_time)
                end_srt = format_srt_time(segment_start_time + chunk_duration)
                srt_content += f"{subtitle_index}\n{start_srt} --> {end_srt}\n{chunk.strip()}\n\n"
                
                subtitle_index += 1
                segment_start_time += chunk_duration

            current_audio_time += segment_duration + 0.05
            
        except Exception as e:
            print(f"Error: {e}")
            continue

    if volume_boost > 0:
        combined_audio = combined_audio + volume_boost
            
    return combined_audio, srt_content

async def generate_audio_final(text, rules, voice_name, tone_val, speed_val, volume_val, filename_val, platform_val):
    if not text.strip(): raise gr.Error("စာရိုက်ထည့်ပါ!")

    target_key = "my-MM-ThihaNeural"
    if "Female" in str(voice_name): target_key = "my-MM-NilarNeural"
    elif "Ryan" in str(voice_name): target_key = "en-GB-RyanNeural"
    elif "Sonia" in str(voice_name): target_key = "en-GB-SoniaNeural"
            
    pitch_str = f"{int(tone_val) * -1:+d}Hz"
    rate_str = f"{int(speed_val):+d}%"
    srt_limit = 150 if "YouTube" in platform_val else 55

    try:
        final_audio, srt_text = await generate_precise_audio(text, rules, target_key, rate_str, pitch_str, volume_val, srt_limit)
        
        output_dir = tempfile.mkdtemp()
        base_name = "output"
        if filename_val and filename_val.strip():
            base_name = "".join(c for c in filename_val if c.isalnum() or c in (' ', '-', '_')).strip()
        
        audio_path = os.path.join(output_dir, f"{base_name}.mp3")
        final_audio.export(audio_path, format="mp3")
        
        srt_path = os.path.join(output_dir, f"{base_name}.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_text)

        # --- USAGE TRACKING LOGIC ---
        global SESSION_COUNT, TOTAL_SECONDS
        
        # ၁။ အကြိမ်အရေအတွက် တိုးမယ်
        SESSION_COUNT += 1
        
        # ၂။ ထွက်လာတဲ့ အသံဖိုင်ရဲ့ အရှည် (စက္ကန့်) ကို ပေါင်းထည့်မယ်
        generated_duration = len(final_audio) / 1000.0 # milliseconds to seconds
        TOTAL_SECONDS += generated_duration
        
        # ၃။ စာတန်းပြောင်းမယ် (Format: XX မိနစ် XX စက္ကန့်)
        duration_str = format_duration_display(TOTAL_SECONDS)
        status_msg = f"📊 သုံးစွဲမှု: {SESSION_COUNT} ကြိမ် | ⏳ စုစုပေါင်းကြာချိန်: {duration_str}"
        
        print(f"\n🔔 [USAGE] Added {generated_duration:.2f}s | Total: {duration_str}\n")
        # ----------------------------

        return audio_path, srt_path, status_msg
        
    except Exception as e:
        raise gr.Error(f"Error: {str(e)}")

with gr.Blocks(title="Myanmar TTS Pro") as demo:
    gr.Markdown("## မြန်မာ TTS Pro (Render HQ)")
    with gr.Row():
        with gr.Column():
            voice = gr.Dropdown([v[0] for v in VOICES], value="အကိုလေး (Male)", label="Voice")
            platform = gr.Radio(["TikTok (9:16)", "YouTube (16:9)"], value="TikTok (9:16)", label="SRT Type")
            
            # Settings (+7, +25, +10)
            tone = gr.Slider(-50, 50, value=7, label="Pitch")
            speed = gr.Slider(-50, 50, value=25, label="Speed")
            vol = gr.Slider(0, 20, value=10, label="Vol Boost")
            
            text = gr.Textbox(lines=5, label="Text")
            rules = gr.Textbox(lines=5, value=DEFAULT_RULES, label="Rules")
            fname = gr.Textbox(label="File Name")
            
            btn = gr.Button("Generate", variant="primary")
            
            # Status Label (Usage Count & Duration)
            lbl_status = gr.Label(value="📊 သုံးစွဲမှု: 0 | ⏳ စုစုပေါင်းကြာချိန်: ၀၀ မိနစ် ၀၀ စက္ကန့်", label="Live Usage Stats")
            
        with gr.Column():
            out_aud = gr.Audio(label="Audio")
            out_srt = gr.File(label="SRT")
            
    btn.click(generate_audio_final, inputs=[text, rules, voice, tone, speed, vol, fname, platform], outputs=[out_aud, out_srt, lbl_status])

if __name__ == "__main__":
    demo.queue(concurrency_count=2).launch(server_name="0.0.0.0", server_port=7860)
