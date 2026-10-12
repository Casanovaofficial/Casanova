"""Speech. Prefers a local neural voice (Piper), falls back to the Windows voice.

Piper runs entirely offline once its voice file is downloaded, and sounds like a
person rather than a 1998 screen reader. If no voice file is present we quietly
use SAPI, so Jarvis always talks.
"""
import logging
import re
import wave
from io import BytesIO
from pathlib import Path

import pyttsx3

log = logging.getLogger("jarvis.tts")

VOICE_DIR = Path("voices")


class Voice:
    def __init__(self, cfg):
        t = cfg["tts"]
        self.rate = t.get("rate", 185)
        self.hints = {"es": t.get("voice_es", ""), "en": t.get("voice_en", "")}
        self.piper = self._load_piper()
        self.voice_ids = {} if self.piper else self._pick_voices()

    # ── the good voice ────────────────────────────
    def _load_piper(self):
        try:
            models = sorted(VOICE_DIR.glob("*.onnx"))
        except Exception:
            return None
        if not models:
            log.info("No Piper voice installed; using the Windows voice. "
                     "Run get_voice.py for a natural one.")
            return None
        try:
            from piper.voice import PiperVoice
            v = PiperVoice.load(str(models[0]))
            log.info("Using neural voice: %s", models[0].name)
            return v
        except Exception as e:
            log.warning("Piper voice present but unusable (%s); using the Windows voice.", e)
            return None

    def _speak_piper(self, text):
        import numpy as np
        import sounddevice as sd
        buf = BytesIO()
        with wave.open(buf, "wb") as wav:
            self.piper.synthesize(text, wav)
        buf.seek(0)
        with wave.open(buf, "rb") as wav:
            sr = wav.getframerate()
            pcm = wav.readframes(wav.getnframes())
        audio = np.frombuffer(pcm, dtype=np.int16)
        sd.play(audio, sr)
        sd.wait()

    # ── the fallback voice ────────────────────────
    def _pick_voices(self):
        eng = pyttsx3.init()
        voices = eng.getProperty("voices")
        eng.stop()
        picked = {}
        for lang, keys in {
                "es": ["spanish", "español", "es_", "es-", "sabina", "helena", "paulina"],
                "en": ["english", "en_", "en-", "zira", "david", "mark", "hazel"]}.items():
            hint = self.hints.get(lang, "").lower()
            for v in voices:
                blob = f"{v.name} {v.id} {getattr(v, 'languages', '')}".lower()
                if (hint and hint in blob) or (not hint and any(k in blob for k in keys)):
                    picked[lang] = v.id
                    break
        log.info("SAPI voices: %s", picked)
        return picked

    def _speak_sapi(self, text, lang):
        # Re-init each time: works around pyttsx3's runAndWait dying after the first call.
        eng = pyttsx3.init()
        eng.setProperty("rate", self.rate)
        vid = self.voice_ids.get(lang or "en") or self.voice_ids.get("en") \
            or self.voice_ids.get("es")
        if vid:
            eng.setProperty("voice", vid)
        eng.say(text)
        eng.runAndWait()
        eng.stop()

    # ── shared ────────────────────────────────────
    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"```.*?```", " ", text, flags=re.S)       # never read code aloud
        text = re.sub(r"[*_#`>|]+", "", text)
        text = re.sub(r"https?://\S+", "the link", text)
        text = re.sub(r"[A-Za-z]:\\[^\s]+", "that file", text)   # don't spell out paths
        return re.sub(r"\s+", " ", text).strip()

    def say(self, text: str, lang: str | None = None):
        text = self._clean(text)
        if not text:
            return
        if self.piper:
            try:
                self._speak_piper(text)
                return
            except Exception as e:
                log.warning("Neural voice failed (%s); falling back.", e)
                self.piper = None
                self.voice_ids = self._pick_voices()
        self._speak_sapi(text, lang)
