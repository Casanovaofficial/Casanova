"""One-time download of the local models (the only step that needs internet)."""
import os
import shutil
import subprocess

import yaml
from faster_whisper import WhisperModel

cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))

print(f"Downloading speech model: {cfg['stt']['model_size']} ...")
WhisperModel(cfg["stt"]["model_size"], device="cpu", compute_type="int8")

exe = shutil.which("ollama") or os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
print(f"Downloading brain model: {cfg['llm']['model']} (several GB) ...")
subprocess.run([exe, "pull", cfg["llm"]["model"]], check=True)
print("Models ready. Jarvis now works fully offline.")
