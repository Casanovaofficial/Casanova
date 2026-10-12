"""Download a natural-sounding local voice for Jarvis (one time, needs internet).

After this, speech is still 100% offline - the voice file lives on your disk.
Run:  .venv\\Scripts\\python get_voice.py            (British male, the Jarvis one)
      .venv\\Scripts\\python get_voice.py ryan       (American male)
      .venv\\Scripts\\python get_voice.py amy        (British female)
      .venv\\Scripts\\python get_voice.py davefx     (Spanish male)
"""
import sys
from pathlib import Path

import requests

BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

VOICES = {
    "alan":   ("en/en_GB/alan/medium/en_GB-alan-medium",      "British male - closest to the films"),
    "ryan":   ("en/en_US/ryan/high/en_US-ryan-high",          "American male, warm"),
    "amy":    ("en/en_GB/amy/medium/en_GB-amy-medium",        "British female"),
    "joe":    ("en/en_US/joe/medium/en_US-joe-medium",        "American male, neutral"),
    "davefx": ("es/es_ES/davefx/medium/es_ES-davefx-medium",  "Spanish male"),
}

name = (sys.argv[1] if len(sys.argv) > 1 else "alan").lower()
if name not in VOICES:
    print("Available voices:")
    for k, (_, desc) in VOICES.items():
        print(f"  {k:8} {desc}")
    sys.exit(1)

path, desc = VOICES[name]
out = Path("voices")
out.mkdir(exist_ok=True)

# Only one voice at a time - Jarvis picks the first .onnx it finds
for old in out.glob("*.onnx*"):
    old.unlink()

for suffix in (".onnx", ".onnx.json"):
    url = f"{BASE}/{path}{suffix}"
    dest = out / (Path(path).name + suffix)
    print(f"Downloading {dest.name} ...")
    r = requests.get(url, stream=True, timeout=180)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    done = 0
    with open(dest, "wb") as f:
        for chunk in r.iter_content(1 << 16):
            f.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done * 100 // total}%", end="", flush=True)
    print("\r  done    ")

print(f"\nInstalled: {name} ({desc})")
print("Restart Jarvis and it will use this voice.")
