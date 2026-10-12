"""Core Jarvis engine.

Runs the listen -> think -> speak loop on a background thread and reports
everything it does through callbacks. The GUI talks only to this class and
never touches the microphone or the model directly, so the engine can also
run headless.
"""
import logging
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import unicodedata

import requests

from brain import Brain
from memory import Memory
from stt import Listener
from tools import Toolbox
from tts import Voice

log = logging.getLogger("jarvis.assistant")

YES = {"yes", "yeah", "yep", "sure", "ok", "okay", "do it", "go ahead", "confirm",
       "affirmative", "si", "claro", "dale", "hazlo"}
EXIT = {"goodbye", "goodbye jarvis", "shut down", "exit assistant", "adios"}
SLEEP = {"stop", "never mind", "nevermind", "cancel", "forget it",
         "para", "cancela", "olvidalo"}
# Stand down until called back. Jarvis keeps listening but acts on nothing else.
STANDBY = {"stand by", "standby", "stand down", "hold on", "hold up", "give me a minute",
           "pause", "go to sleep", "quiet", "shush", "espera", "aguanta"}
RESUME = {"im back", "i am back", "wake up", "resume", "continue", "carry on",
           "you there", "are you there", "lets go", "ya volvi", "despierta"}

# Status strings the GUI renders as a coloured pill
LOADING, LISTENING, THINKING, SPEAKING, MUTED, STOPPED, GOAHEAD, STANDBY_STATUS = (
    "Loading", "Listening", "Thinking", "Speaking", "Mic off", "Stopped", "Go ahead",
    "Standing by")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^\w\s]", "", s).strip()


class Assistant:
    """The engine. Create it, give it callbacks, call start()."""

    def __init__(self, cfg, on_event=None, on_status=None, on_confirm=None):
        self.cfg = cfg
        self.name = cfg["assistant_name"]
        # on_event(kind, text) where kind is: you | jarvis | system | tool | error
        self.on_event = on_event or (lambda *a: None)
        self.on_status = on_status or (lambda *a: None)
        # on_confirm(question) -> bool, used for typed commands (voice uses the mic)
        self.on_confirm = on_confirm

        self.wake = re.compile(
            r"^\W*(?:(?:hey|hi|ok|okay|oye|hola)\W+)?(?:" +
            "|".join(map(re.escape, cfg["wake_words"])) + r")\b\W*", re.I)

        self._stop = threading.Event()
        self._mic_on = threading.Event()
        self._mic_on.set()
        self._text_q: "queue.Queue[str]" = queue.Queue()
        self._force_listen = threading.Event()   # hotkey: next thing heard is a command
        self._force_until = 0.0                  # ...but only for a few seconds
        self._last_interaction = time.time()
        self._busy = threading.Lock()
        self._last_suggestion = 0.0
        self._standby = False
        self._thread = None
        self._source = "voice"

        self.listener = None
        self.voice = None
        self.brain = None
        self.ready = False

    # ── public API ────────────────────────────────────────────
    def start(self):
        self._thread = threading.Thread(target=self._run, name="jarvis-engine", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def send_text(self, text: str):
        """Queue a typed command, exactly as if it had been spoken."""
        if text.strip():
            self._text_q.put(text.strip())

    def reload_config(self):
        """Re-read anything that can change while running (wake words, name, limits)."""
        self.name = self.cfg["assistant_name"]
        words = list(self.cfg.get("wake_words") or [])
        if self.name.lower() not in words:
            words.append(self.name.lower())
        self.wake = re.compile(
            r"^\W*(?:(?:hey|hi|ok|okay|oye|hola)\W+)?(?:" +
            "|".join(map(re.escape, words)) + r")\b\W*", re.I)
        self.on_event("system", "Settings reloaded.")

    ARM_SECONDS = 15

    def talk_now(self):
        """Mic button or hotkey. Press again while armed to cancel."""
        if self._force_listen.is_set():
            return self.cancel_listen()
        if not self.ready:
            self.on_event("system", "Still starting up - give it a few seconds.")
            return
        self._standby = False
        if not self._mic_on.is_set():
            self._mic_on.set()
            self.on_event("system", "Microphone turned back on.")
        self._force_listen.set()
        self._force_until = time.time() + self.ARM_SECONDS
        self.on_event("system", "Listening - go ahead.")
        self.on_status(GOAHEAD)

    def cancel_listen(self):
        """Stop waiting, without shutting anything down."""
        self._force_listen.clear()
        self._force_until = 0.0
        self.on_event("system", "Cancelled.")
        self.on_status(LISTENING if self._mic_on.is_set() else MUTED)

    def set_mic(self, enabled: bool):
        if enabled:
            self._mic_on.set()
            self.on_event("system", "Microphone on.")
            if self.ready:
                self.on_status(LISTENING)
        else:
            self._mic_on.clear()
            self.on_event("system", "Microphone off. You can still type commands.")
            self.on_status(MUTED)

    @property
    def mic_on(self) -> bool:
        return self._mic_on.is_set()

    # ── startup ───────────────────────────────────────────────
    def _ensure_ollama(self) -> bool:
        host = self.cfg["llm"]["host"]

        def up():
            try:
                return requests.get(f"{host}/api/tags", timeout=2).ok
            except Exception:
                return False

        if up():
            return True
        self.on_event("system", "Starting Ollama...")
        exe = shutil.which("ollama") or os.path.expandvars(
            r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
        try:
            subprocess.Popen([exe, "serve"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             creationflags=0x08000000 if os.name == "nt" else 0)
        except Exception as e:
            log.error("Could not start Ollama: %s", e)
            return False
        for _ in range(30):
            if self._stop.is_set():
                return False
            time.sleep(1)
            if up():
                return True
        return False

    def _speak(self, text, lang="en"):
        """Say something out loud without hearing ourselves."""
        log.info("SAY: %s", text)
        if self.listener:
            self.listener.pause()
        try:
            self.voice.say(text, lang)
        except Exception as e:
            log.exception("TTS failed")
            self.on_event("error", f"Could not speak: {e}")
        finally:
            if self.listener and self._mic_on.is_set():
                self.listener.resume()

    def _confirm(self, question: str) -> bool:
        """Ask before anything destructive. Typed commands get a dialog, spoken ones the mic."""
        self.on_event("system", question)
        if self._source == "text" and self.on_confirm:
            return bool(self.on_confirm(question))
        self._speak(question)
        for _ in range(2):
            answer, _, _ = self.listener.listen(timeout=8)
            if answer:
                self.on_event("you", answer)
                words = [norm(answer)] + norm(answer).split()
                return any(w in YES for w in words)
        return False

    def route(self, heard: str, started: float | None, awake_until: float):
        """Decide what a heard sentence means.

        Returns the command text, "" if Jarvis was addressed with nothing after
        its name, or None if the sentence was not meant for Jarvis at all.
        There are three ways in: the wake word, the hotkey, and the few seconds
        of follow-up after it has just answered.
        """
        m = self.wake.match(heard)
        if self._force_listen.is_set():                 # hotkey armed: take it either way
            self._force_listen.clear()
            self._force_until = 0.0
            return heard[m.end():].strip() if m else heard
        if m:
            return heard[m.end():].strip()
        if started is not None and started <= awake_until:
            return heard                                # follow-up, no wake word needed
        return None

    # ── the loop ──────────────────────────────────────────────
    def _run(self):
        try:
            self.on_status(LOADING)
            self.on_event("system", "Loading the speech model, about 30 seconds...")
            self.listener = Listener(self.cfg)
            self.voice = Voice(self.cfg)
            memory = Memory(self.cfg)
            tools = Toolbox(self.cfg, self._confirm, memory,
                            on_tool=lambda n, a: self.on_event("tool", f"{n} {a or ''}".strip()),
                            on_reload=self.reload_config)
            self.brain = Brain(self.cfg, tools, memory)
        except Exception as e:
            log.exception("Startup failed")
            self.on_status(STOPPED)
            self.on_event("error", f"Could not start: {e}")
            return

        with self.listener:
            if self._ensure_ollama():
                self.brain.warm_up()
                self.ready = True
                self.on_event("system", f"{self.name} is online. Say \"{self.name}\" to wake it.")
                self._speak(f"{self.name} online.")
            else:
                self.ready = True
                self.on_event("error", "Ollama is not running, so I can hear you but not think. "
                                       "Open Ollama and restart Jarvis.")
            self.on_status(LISTENING if self._mic_on.is_set() else MUTED)

            if getattr(self.listener, "fallback_reason", ""):
                self.on_event("system", self.listener.fallback_reason)

            threading.Thread(target=self._observer, name="jarvis-observer",
                             daemon=True).start()

            awake_until = 0.0
            consecutive_errors = 0
            while not self._stop.is_set():
                try:
                    awake_until = self._tick(awake_until)
                except Exception as e:
                    consecutive_errors += 1
                    log.exception("Error in the listening loop")
                    self.on_event("error", f"{type(e).__name__}: {e}")
                    if consecutive_errors >= 5:
                        self.on_event("error", "Too many failures in a row - stopping. "
                                               "See data/jarvis.log.")
                        break
                    time.sleep(1)
                else:
                    consecutive_errors = 0

        self.on_status(STOPPED)
        self.on_event("system", "Jarvis stopped.")

    def _tick(self, awake_until: float) -> float:
        """One pass of the listen/think/speak loop.

        Returns the new follow-up deadline. Raises nothing the caller cannot
        survive: _run catches anything and keeps the loop alive, so one bad
        sentence can never take the assistant down silently.
        """
        follow_up = lambda: time.time() + self.cfg["follow_up_s"]

        # 1. Typed commands take priority and work even with the mic off
        try:
            self._handle(self._text_q.get_nowait(), "text")
            return follow_up()
        except queue.Empty:
            pass

        # 2. Microphone
        if not self._mic_on.is_set():
            self.listener.pause()
            time.sleep(0.2)
            return awake_until
        if self.listener.muted:
            self.listener.resume()

        heard, lang, started = self.listener.listen(timeout=1.0)

        if self._force_listen.is_set() and time.time() > self._force_until:
            self._force_listen.clear()
            self._force_until = 0.0
            self.on_event("system", "Stopped waiting - nothing heard.")
            self.on_status(LISTENING if self._mic_on.is_set() else MUTED)

        if not heard:
            return awake_until
        log.info("HEARD: %s", heard)

        cmd = self.route(heard, started, awake_until)
        if cmd is None:
            self.on_event("system", f"(ignored, no wake word) {heard}")
            return awake_until

        if not cmd:                                  # addressed by name, nothing after it
            self.on_event("you", heard)
            self._speak("Yes?")
            return follow_up()

        n = norm(cmd)

        # Standing by: ignore everything until called back by name or phrase
        if self._standby:
            if n in RESUME or any(r in n for r in RESUME):
                self._standby = False
                self.on_event("system", "Back.")
                self._speak("I'm here.")
                self.on_status(LISTENING)
                return follow_up()
            return awake_until
        if n in STANDBY or any(s == n for s in STANDBY):
            self._standby = True
            self.on_event("system", 'Standing by. Say "wake up" when you need me.')
            self._speak("Standing by.")
            self.on_status(STANDBY_STATUS)
            return 0.0

        if n in EXIT:
            self.on_event("you", cmd)
            self._speak("Goodbye.")
            self._stop.set()
            return awake_until
        if n in SLEEP:
            self.on_event("you", cmd)
            return 0.0

        self._handle(cmd, "voice")
        return follow_up()

    # ── noticing things on its own ────────────────────────────
    def _observer(self):
        """Every so often, look at the screen and speak only if it is genuinely worth it.

        Deliberately conservative: it stays quiet unless the model clears a high bar,
        never interrupts a conversation, and never fires twice in a row quickly.
        """
        cfg = self.cfg.get("proactive") or {}
        if not cfg.get("enabled", False):
            return
        every = max(60, int(cfg.get("interval_minutes", 20)) * 60)
        quiet_for = max(60, int(cfg.get("only_after_idle_minutes", 5)) * 60)

        while not self._stop.wait(30):
            if not self.ready or not self._mic_on.is_set() or self._standby:
                continue
            now = time.time()
            if now - self._last_suggestion < every:
                continue
            if now - self._last_interaction < quiet_for:
                continue          # they are mid-conversation; do not butt in
            if self._busy.locked():
                continue
            self._last_suggestion = now
            try:
                import context as ctx
                note = self.brain.suggest(ctx.describe())
            except Exception:
                log.exception("Observer failed")
                continue
            if note:
                log.info("SUGGESTION: %s", note)
                self.on_event("jarvis", note)
                self._speak(note)

    def _handle(self, cmd: str, source: str):
        self._last_interaction = time.time()
        self._source = source
        self.on_event("you", cmd)
        self.on_status(THINKING)
        with self._busy:
            return self._think_and_speak(cmd)

    def _think_and_speak(self, cmd: str):
        try:
            reply = self.brain.chat(cmd)
        except Exception as e:
            log.exception("Brain error")
            reply = f"Something failed: {e}"
            self.on_event("error", reply)
        else:
            self.on_event("jarvis", reply)
        self.on_status(SPEAKING)
        self._speak(reply)
        self._last_interaction = time.time()
        self.on_status(LISTENING if self._mic_on.is_set() else MUTED)
