"""Microphone check: proves whether Jarvis can hear you, and what it thinks you said."""
import sys

import numpy as np
import sounddevice as sd
import yaml

SECONDS = 5

print("=" * 58)
print("  MICROPHONE CHECK")
print("=" * 58)

# ── 1. Which input devices does Windows expose? ───────────────
print("\nInput devices found:\n")
default_in = None
try:
    default_in = sd.default.device[0]
except Exception:
    pass

found = False
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        found = True
        mark = "  <-- DEFAULT (this is the one Jarvis uses)" if i == default_in else ""
        print(f"  [{i}] {d['name']}{mark}")

if not found:
    print("  NONE. Windows is not giving Python any microphone.")
    print("\n  Fix: Settings > Privacy & security > Microphone")
    print("       Turn ON 'Microphone access' AND 'Let desktop apps access your microphone'.")
    input("\nPress Enter to close")
    sys.exit(1)

# ── 2. Record and measure ─────────────────────────────────────
cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
sr = cfg["audio"]["sample_rate"]

print(f"\nRecording for {SECONDS} seconds. SAY SOMETHING NOW, normal speaking voice:\n")
try:
    audio = sd.rec(int(SECONDS * sr), samplerate=sr, channels=1, dtype="float32")
    for s in range(SECONDS, 0, -1):
        print(f"   {s}...", flush=True)
        sd.sleep(1000)
    sd.wait()
except Exception as e:
    print(f"\n  RECORDING FAILED: {e}")
    print("  Usually means Windows is blocking microphone access for desktop apps.")
    input("\nPress Enter to close")
    sys.exit(1)

audio = audio.flatten()
peak = float(np.abs(audio).max())
rms = float(np.sqrt((audio ** 2).mean()))
bars = int(min(peak, 1.0) * 40)
print(f"\n  Level: [{'#' * bars}{'.' * (40 - bars)}]  peak={peak:.3f}")

if peak < 0.01:
    print("\n  SILENCE. The microphone captured nothing at all.")
    print("  - Check Windows microphone privacy settings for desktop apps")
    print("  - Check the right mic is set as DEFAULT in Windows sound settings")
    print("  - Check it is not muted or unplugged")
    input("\nPress Enter to close")
    sys.exit(1)

if peak < 0.05:
    print("\n  VERY QUIET. Jarvis will probably miss you.")
    print("  Raise the microphone volume in Windows sound settings, or move closer.")

# ── 3. Can Whisper actually transcribe it? ────────────────────
print(f"\n  Loading the speech model (first run takes ~30 seconds)...")
from faster_whisper import WhisperModel

model = WhisperModel(cfg["stt"]["model_size"], device="cpu", compute_type="int8")
lang = None if cfg.get("language", "auto") == "auto" else cfg["language"]
segments, info = model.transcribe(audio, language=lang, beam_size=1)
text = " ".join(s.text for s in segments).strip()

print("\n" + "=" * 58)
if text:
    print(f'  IT HEARD:  "{text}"')
    print("\n  The microphone works. If Jarvis still ignores you, the")
    print("  wake word is the problem - check data/jarvis.log to see")
    print("  how it spells your 'Jarvis', then add that spelling to")
    print("  wake_words in config.yaml.")
else:
    print("  Audio came through, but the model transcribed nothing.")
    print("  Try again and speak louder and closer to the microphone.")
print("=" * 58)
input("\nPress Enter to close")
