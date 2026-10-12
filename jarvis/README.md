# Jarvis - Offline Voice Assistant (English)

Listens for its name, answers out loud, and controls your PC.
**100% local** - no internet, no API key, no credits once installed.

Jarvis starts with Windows and opens a **control window**: you can see its
status live, read everything it hears and says, and type commands instead of
speaking. Closing the window hides it to the system tray - it keeps listening.

## Install

1. Extract this folder somewhere simple, like `C:\Jarvis`
2. Double-click **`INSTALL.bat`**
3. Wait 10-20 minutes (it downloads about 5 GB of models)

If Windows shows "Windows protected your PC", click **More info** -> **Run anyway**.

## The control files

| File | What it does |
|---|---|
| **Desktop / Start menu icon** | Opens Jarvis (or surfaces the mic panel) |
| **JARVIS.bat** | The same thing, from the folder |
| **STOP_JARVIS.bat** | Shuts Jarvis down completely |
| **TEST_JARVIS.bat** | Opens it with the technical log visible, for troubleshooting |
| **CHECK_MIC.bat** | Tests your microphone and prints what it understood |
| **INSTALL.bat** | Install or repair |

### The mic panel

The everyday face of Jarvis is a small floating bar, always on top: a
microphone button, a gear, and a help button. Click the microphone and talk.
Drag the bar at the top to move it; it remembers where you put it. The X hides
it - Jarvis keeps listening and the tray icon brings it back.

### The hotkey

Press **Win + Alt + J** anywhere in Windows - in any app, with the panel hidden
- and it comes up listening. No wake word needed, just talk.

Win + Alt + J is deliberate: Windows claims no `Win + Alt + <letter>`
combination at all, so it cannot collide with a built-in shortcut the way
Win + H (voice typing) or Win + C would. **Ctrl + Alt + J** does the same thing
if you prefer it. Change either in Settings or in `config.yaml` under `hotkeys`.

### Finding it in your apps

The installer puts Jarvis in three places, all with its own icon: your
**Desktop**, your **Start menu** (press Start and type "jarvis"), and
**Startup**, so it comes back on its own every time you log in.

### Settings - change Jarvis by telling it

The gear on the mic panel opens Settings, which works two ways:

- **The form** - name, hotkey, language, model, speaking speed, how long the
  follow-up window stays open, whether it asks before risky actions.
- **The chat box** - just say what you want changed and Jarvis changes itself:
  *"keep your answers to one sentence"*, *"stop asking before you open apps"*,
  *"you also answer to Travis"*, *"speak slower"*, *"use the bigger model"*.

Standing instructions you give it that way are permanent and shape every future
reply. "Reset everything" undoes the lot.

Your `config.yaml` is never rewritten - it stays as the documented defaults.
Changes are stored separately in `data\overrides.json`, so deleting that one
file undoes everything.

### The console window

- **Status pill** top-right: Loading / Listening / Thinking / Speaking / Mic off
- **Transcript** of everything, colour-coded: you, Jarvis, actions it took, errors
- **Type box** - send a command without speaking. Useful when the mic is off,
  and the fastest way to tell whether the brain works independently of the microphone.
- **Microphone button** - mute it without shutting Jarvis down
- **Hide to tray** - the icon sits by the clock; click it to bring the window back

Only one copy ever runs. Opening the app again surfaces the existing window
rather than starting a second one.

## It knows what you are doing

Before every reply Jarvis reads the window you have in front, your other open
windows, and your clipboard. So "close this", "save it here", "what am I
looking at" and "summarise what I copied" resolve to the real thing instead of
a confused question.

It is also told to act rather than narrate: if there is a tool for what you
asked, it uses it and reports in past tense, chaining several steps when the
job needs them. It will do what you asked first and then tell you in one
sentence if it thinks there was a better way.

## Talking to it

Say **"Jarvis"** first, then your request:

| Say | What happens |
|---|---|
| "Jarvis, what time is it" | answers out loud |
| "Jarvis, open Spotify" | opens the app |
| "Jarvis, how is my computer doing" | CPU / RAM / disk / battery |
| "Jarvis, find my invoice PDFs" | searches your files |
| "Jarvis, turn the volume up" | media and volume keys |
| "Jarvis, remember my client folder is D:\Clients" | permanent memory |
| "stop" / "never mind" | cancels |
| "goodbye Jarvis" | shuts it down |

After it answers you have 10 seconds to keep talking without saying the name again.
Before deleting files, closing programs, or running risky commands it asks out loud and waits for a yes.

## It doesn't respond

Work through these in order:

1. **Open the console (gear, then the Console button) and type a command** (for example `what time is it`).
   If it answers, the brain is fine and the problem is only the microphone.
2. **Run `CHECK_MIC.bat`.** It records you for 5 seconds and prints what it heard.
   This separates "the mic is dead" from "it can't recognize its name".
3. **Microphone blocked?** Windows Settings -> Privacy & security -> Microphone.
   Both *Microphone access* and *Let desktop apps access your microphone* must be ON.
4. **Run `TEST_JARVIS.bat`** and watch the window while you talk. Lines starting
   with `HEARD` show what it understood. If `HEARD` shows your words but nothing
   happens, it didn't recognize the wake word - see below.
5. **Wake word.** If the log shows it hearing "Travis" or "Service" instead of
   "Jarvis", open `config.yaml` and add that spelling to `wake_words`.
6. **Logs** are in `data\jarvis.log`.

## Settings

Everything lives in `config.yaml`:

- `language: en` - set to `es` for Spanish, or `auto` to detect per sentence
- `user_name` - what it calls you
- `hotkey` - the global shortcut, pynput syntax (`<ctrl>+<alt>+j`)
- `llm.model` - `qwen2.5:7b` is the default. `qwen2.5:3b` on a weaker PC;
  `qwen2.5:14b` or `qwen2.5:32b` if you have the GPU for it - bigger models
  follow multi-step instructions noticeably better. Run
  `ollama pull <model>` first, then change this line.
- `stt.model_size` - `small` default. Use `base` if transcription is slow.
- `wake_words` - add spellings if it mishears its name
- `safety.confirm_dangerous` - set to `false` to stop it asking before risky actions

After changing anything, run `STOP_JARVIS.bat` then `JARVIS.bat` to reload it.

## Speeding up transcription with your GPU

If you have an NVIDIA card, Jarvis tries the GPU first and automatically falls
back to the processor when CUDA's maths libraries are missing - it still works,
just takes a second or two longer per sentence. To get the GPU working, open
PowerShell in this folder and run:

```
.venv\Scripts\python -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

That is about 700 MB. Restart Jarvis afterwards; the log will say
"GPU transcription works." instead of falling back.

## Hardware

- Minimum: 16 GB RAM with `qwen2.5:3b` and `stt.model_size: base`
- Recommended: NVIDIA GPU with 8 GB+, the defaults as shipped

## Adding abilities

Add a method with the `@tool(...)` decorator in `tools.py`. The model picks it
up automatically - no other wiring needed.
