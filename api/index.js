// Main Handler
module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send("Method Not Allowed");

  try {
    // ၁. Library ကို ဒီနေရာမှာ ခေါ်မှ Error တက်ရင် သိရမှာပါ
    const { MsEdgeTTS, OUTPUT_FORMAT } = require("msedge-tts");

    const { text, rules, voice, speed, pitch } = req.body;
    if (!text) return res.status(400).json({ error: "စာရိုက်ထည့်ပါ" });

    // Helper Functions (Inside handler to be safe)
    const applyPronunciationRules = (txt, rls) => {
      if (!rls) return txt;
      let f = txt;
      rls.split('\n').forEach(l => {
        const [k, v] = l.split('=').map(s => s.trim());
        if (k && v) f = f.split(k).join(v);
      });
      return f;
    };

    const splitByPunctuation = (txt) => {
      const parts = txt.split(/([!။.;!?၊])/);
      const segs = [];
      let cur = "";
      parts.forEach(p => {
        if (!p) return;
        if (['။', '.', '!', ';', '?', '၊'].includes(p)) {
          if (cur) { segs.push((cur + p).trim()); cur = ""; }
          else if (segs.length) segs[segs.length - 1] += p;
        } else cur += p;
      });
      if (cur.trim()) segs.push(cur.trim());
      return segs;
    };

    // Voice Setup
    let voiceKey = "my-MM-ThihaNeural";
    if (voice && (voice.includes("Female") || voice.includes("Nilar"))) voiceKey = "my-MM-NilarNeural";
    else if (voice && voice.includes("Ryan")) voiceKey = "en-GB-RyanNeural";
    else if (voice && voice.includes("Sonia")) voiceKey = "en-GB-SoniaNeural";

    const rateStr = `${parseInt(speed) >= 0 ? '+' : ''}${parseInt(speed)}%`;
    const pitchStr = `${parseInt(pitch) * -1 >= 0 ? '+' : ''}${parseInt(pitch) * -1}Hz`;
    
    const cleanText = text.replace(/\n/g, " ");
    const segments = splitByPunctuation(cleanText);
    const audioBuffers = [];

    // TTS Setup
    const tts = new MsEdgeTTS();
    await tts.setMetadata(voiceKey, OUTPUT_FORMAT.AUDIO_24KHZ_48BIT_MONO_MP3);

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

    const finalBuffer = Buffer.concat(audioBuffers);
    res.json({ audio: finalBuffer.toString('base64') });

  } catch (e) {
    // Error တက်ရင် ဒီနေရာကနေ အကြောင်းပြန်ပါလိမ့်မယ်
    console.error(e);
    res.status(500).json({ error: "Backend Error: " + e.message });
  }
};
