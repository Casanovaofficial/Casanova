"""Offline speech-to-text: microphone -> voice activity detection -> Whisper (local)."""
import collections
import logging
import queue
import time

import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

log = logging.getLogger("jarvis.stt")

# Whisper hallucinates these on pure noise; ignore when they are the whole utterance.
NOISE_PHRASES = {"gracias.", "thank you.", "thanks for watching!", "you", ".", "subtítulos realizados por la comunidad de amara.org"}


class Listener:
    FRAME_MS = 30

    def __init__(self, cfg):
        a, s = cfg["audio"], cfg["stt"]
        self.sr = a["sample_rate"]
        self.frame_len = int(self.sr * self.FRAME_MS / 1000)
        self.vad = webrtcvad.Vad(a["vad_aggressiveness"])
        self.silence_frames = a["silence_ms"] // self.FRAME_MS
        self.max_frames = int(a["max_utterance_s"] * 1000 / self.FRAME_MS)
        self.lang = None if cfg.get("language", "auto") == "auto" else cfg["language"]

        device = s["device"]
        if device == "auto":
            try:
                import ctranslate2
                device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except Exception:
                device = "cpu"
        self.size = s["model_size"]
        self.cpu_compute = s["compute_type"]
        self.device = device
        self._load(device)
        self._prove_it_works()

        self.fallback_reason = ""
        self.q: "queue.Queue[bytes]" = queue.Queue()
        self.muted = False
        self.stream = None

    def _load(self, device):
        compute = self.cpu_compute if device == "cpu" else "float16"
        log.info("Loading Whisper '%s' on %s (%s)", self.size, device, compute)
        self.model = WhisperModel(self.size, device=device, compute_type=compute)
        self.device = device

    def _prove_it_works(self):
        """Transcribe a moment of silence at startup.

        A GPU build can load happily and only fail later, deep in the first real
        transcription, if CUDA's cuBLAS/cuDNN libraries are missing - which looks
        to the user like the assistant simply ignoring them. Better to find out
        now and quietly fall back to the CPU, which always works.
        """
        if self.device == "cpu":
            return
        try:
            silence = np.zeros(self.sr, dtype=np.float32)
            list(self.model.transcribe(silence, language="en", beam_size=1)[0])
            log.info("GPU transcription works.")
        except Exception as e:
            log.warning("GPU transcription unavailable (%s). Falling back to CPU.", e)
            self.fallback_reason = (
                "Your GPU is missing the CUDA libraries Whisper needs, so I am "
                "listening with the processor instead. It still works.")
            try:
                self._load("cpu")
            except Exception:
                log.exception("CPU fallback also failed")
                raise

    # ── stream lifecycle ──────────────────────────
    def __enter__(self):
        self.stream = sd.RawInputStream(samplerate=self.sr, blocksize=self.frame_len,
                                        dtype="int16", channels=1, callback=self._cb)
        self.stream.start()
        return self

    def __exit__(self, *exc):
        if self.stream:
            self.stream.stop()
            self.stream.close()

    def _cb(self, indata, frames, t, status):
        if not self.muted:
            self.q.put(bytes(indata))

    def pause(self):
        """Stop hearing ourselves while Jarvis speaks."""
        self.muted = True

    def resume(self):
        self._drain()
        self.muted = False

    def _drain(self):
        while True:
            try:
                self.q.get_nowait()
            except queue.Empty:
                break

    # ── listening ─────────────────────────────────
    def listen(self, timeout=None):
        """Block until one spoken sentence is captured.
        Returns (text, language, started_at). Empty text on timeout/noise."""
        ring = collections.deque(maxlen=10)          # 300 ms pre-roll
        voiced, triggered, silent, started = [], False, 0, None
        deadline = time.time() + timeout if timeout else None

        while True:
            if deadline and not triggered and time.time() > deadline:
                return "", None, None
            try:
                frame = self.q.get(timeout=0.5)
            except queue.Empty:
                continue
            if len(frame) != self.frame_len * 2:
                continue
            speech = self.vad.is_speech(frame, self.sr)

            if not triggered:
                ring.append((frame, speech))
                if sum(sp for _, sp in ring) >= 6:
                    triggered, started = True, time.time() - 0.3
                    voiced = [f for f, _ in ring]
                    ring.clear()
            else:
                voiced.append(frame)
                silent = 0 if speech else silent + 1
                if silent >= self.silence_frames or len(voiced) >= self.max_frames:
                    break

        text, lang = self._transcribe(b"".join(voiced))
        return text, lang, started

    def _transcribe(self, pcm: bytes):
        audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
        if len(audio) < self.sr * 0.5:
            return "", None
        try:
            segments, info = self.model.transcribe(audio, language=self.lang, beam_size=1,
                                                   condition_on_previous_text=False)
            segments = list(segments)
        except RuntimeError as e:
            # Last-resort net: if the GPU dies mid-session, drop to the CPU and retry
            # once rather than taking the whole assistant down.
            if self.device == "cpu":
                log.exception("Transcription failed")
                return "", None
            log.warning("GPU transcription failed (%s). Switching to CPU.", e)
            self._load("cpu")
            segments, info = self.model.transcribe(audio, language=self.lang, beam_size=1,
                                                   condition_on_previous_text=False)
            segments = list(segments)
        text = " ".join(seg.text for seg in segments).strip()
        if text.lower() in NOISE_PHRASES:
            return "", None
        return text, info.language
