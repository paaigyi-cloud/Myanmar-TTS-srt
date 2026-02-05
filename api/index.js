const { MsEdgeTTS, OUTPUT_FORMAT } = require("edge-tts");

// အသံထွက် ပြင်ဆင်ခြင်း (Rules)
function applyPronunciationRules(text, rulesStr) {
  if (!rulesStr) return text;
  let fixedText = text;
  const lines = rulesStr.split('\n');
  lines.forEach(line => {
    if (line.includes('=')) {
      const parts = line.split('=');
      const key = parts[0].trim();
      const val = parts[1].trim();
      if (key && val) {
        fixedText = fixedText.split(key).join(val);
      }
    }
  });
  return fixedText;
}

// SRT အချိန် တွက်ချက်ခြင်း
function formatSrtTime(totalSeconds) {
  const millis = Math.floor((totalSeconds % 1) * 1000);
  const seconds = Math.floor(totalSeconds) % 60;
  const minutes = Math.floor(totalSeconds / 60) % 60;
  const hours = Math.floor(totalSeconds / 3600);
  const pad = (num, size) => ('000' + num).slice(size * -1);
  return `${pad(hours, 2)}:${pad(minutes, 2)}:${pad(seconds, 2)},${pad(millis, 3)}`;
}

// စာကြောင်းဖြတ်ခြင်း (ပုဒ်ဖြတ်ပုဒ်ရပ် အလိုက်)
function splitByPunctuation(text) {
  const parts = text.split(/([!။.;!?၊])/);
  const segments = [];
  let current = "";
  parts.forEach(part => {
    if (!part) return;
    if (['။', '.', '!', ';', '?', '၊'].includes(part)) {
      if (current) {
        segments.push((current + part).trim());
        current = "";
      } else if (segments.length > 0) {
        segments[segments.length - 1] += part;
      }
    } else {
      current += part;
    }
  });
  if (current.trim()) segments.push(current.trim());
  return segments;
}

// SRT စာကြောင်း ခွဲခြင်း
function smartSplitTextForSrt(text, maxChars) {
  const words = text.split(' ');
  const segments = [];
  let current = "";
  words.forEach(word => {
    if ((current.length + word.length) < maxChars) {
      current += word + " ";
    } else {
      if (current.trim()) segments.push(current.trim());
      current = word + " ";
    }
  });
  if (current.trim()) segments.push(current.trim());
  return segments;
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send("Method Not Allowed");

  try {
    const { text, rules, voice, speed, pitch, platform } = req.body;
    if (!text) return res.status(400).json({ error: "စာရိုက်ထည့်ပါ" });

    // Voice Setup
    let voiceKey = "my-MM-ThihaNeural";
    if (voice.includes("Female") || voice.includes("Nilar")) voiceKey = "my-MM-NilarNeural";
    else if (voice.includes("Ryan")) voiceKey = "en-GB-RyanNeural";
    else if (voice.includes("Sonia")) voiceKey = "en-GB-SoniaNeural";

    const rateStr = `${parseInt(speed) >= 0 ? '+' : ''}${parseInt(speed)}%`;
    const pitchStr = `${parseInt(pitch) * -1 >= 0 ? '+' : ''}${parseInt(pitch) * -1}Hz`;
    
    const cleanText = text.replace(/\n/g, " ");
    const segments = splitByPunctuation(cleanText);
    
    let srtContent = "";
    let srtIndex = 1;
    let currentTime = 0;
    const audioBuffers = [];
    const srtLimit = platform.includes("YouTube") ? 150 : 55;

    const tts = new MsEdgeTTS();
    await tts.setMetadata(voiceKey, OUTPUT_FORMAT.AUDIO_24KHZ_48BIT_MONO_MP3);

    for (const segment of segments) {
      if (!segment.trim()) continue;
      
      const speakableText = applyPronunciationRules(segment, rules);
      const result = await tts.toStream(speakableText, { rate: rateStr, pitch: pitchStr });
      
      const chunks = [];
      for await (const chunk of result.stream) chunks.push(chunk);
      audioBuffers.push(Buffer.concat(chunks));

      // Time Estimation (1 char ~ 0.15s approx without FFmpeg)
      const estimatedDuration = speakableText.length * 0.15; 
      const srtChunks = smartSplitTextForSrt(segment, srtLimit);
      const totalChars = segment.length || 1;
      
      let segStartTime = currentTime;
      for (const chunk of srtChunks) {
        const chunkDuration = (chunk.length / totalChars) * estimatedDuration;
        srtContent += `${srtIndex}\n${formatSrtTime(segStartTime)} --> ${formatSrtTime(segStartTime + chunkDuration)}\n${chunk.trim()}\n\n`;
        srtIndex++;
        segStartTime += chunkDuration;
      }
      currentTime += estimatedDuration + 0.1; // small pause buffer
    }

    res.json({
      audio: Buffer.concat(audioBuffers).toString('base64'),
      srt: srtContent
    });

  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
