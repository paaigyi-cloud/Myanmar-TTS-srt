const { MsEdgeTTS, OUTPUT_FORMAT } = require("msedge-tts");

// အသံထွက် ပြင်ဆင်ခြင်း Helper
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

// စာကြောင်းဖြတ် Helper
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

// Main Logic
module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send("Method Not Allowed");

  try {
    const { text, rules, voice, speed, pitch } = req.body;
    if (!text) return res.status(400).json({ error: "စာရိုက်ထည့်ပါ" });

    // Voice Selection
    let voiceKey = "my-MM-ThihaNeural";
    if (voice && (voice.includes("Female") || voice.includes("Nilar"))) voiceKey = "my-MM-NilarNeural";
    else if (voice && voice.includes("Ryan")) voiceKey = "en-GB-RyanNeural";
    else if (voice && voice.includes("Sonia")) voiceKey = "en-GB-SoniaNeural";

    // Rate & Pitch Formatting
    const rateStr = `${parseInt(speed) >= 0 ? '+' : ''}${parseInt(speed)}%`;
    const pitchStr = `${parseInt(pitch) * -1 >= 0 ? '+' : ''}${parseInt(pitch) * -1}Hz`;
    
    // Process Text
    const cleanText = text.replace(/\n/g, " ");
    const segments = splitByPunctuation(cleanText);
    const audioBuffers = [];

    // TTS Setup
    const tts = new MsEdgeTTS();
    await tts.setMetadata(voiceKey, OUTPUT_FORMAT.AUDIO_24KHZ_48BIT_MONO_MP3);

    // Generation Loop
    for (const segment of segments) {
      if (!segment.trim()) continue;
      
      const speakableText = applyPronunciationRules(segment, rules);
      const result = await tts.toStream(speakableText, { rate: rateStr, pitch: pitchStr });
      
      const chunks = [];
      for await (const chunk of result.stream) {
        chunks.push(chunk);
      }
      audioBuffers.push(Buffer.concat(chunks));
    }

    // Return Audio
    const finalBuffer = Buffer.concat(audioBuffers);
    res.json({
      audio: finalBuffer.toString('base64')
    });

  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
};
