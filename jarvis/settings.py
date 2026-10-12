"""Settings Jarvis can change about itself.

config.yaml stays as the documented defaults and is never rewritten by the
program. Anything changed at runtime - by you in the Settings window, or by
Jarvis because you told it to - is stored as an overlay in data/overrides.json
and merged on top at load time. That way your commented config file survives,
and a bad change can be undone by deleting one small file.
"""
import json
import logging
from pathlib import Path

import yaml

log = logging.getLogger("jarvis.settings")

OVERRIDES = Path("data/overrides.json")

# name -> (type, help shown to the user, does it need a restart)
EDITABLE = {
    "assistant_name":           (str,   "What you call it. Also becomes a wake word.", True),
    "user_name":                (str,   "What it calls you.", False),
    "hotkey":                   (str,   "Global shortcut, e.g. <ctrl>+<alt>+j", True),
    "language":                 (str,   "en, es, or auto to detect per sentence.", True),
    "follow_up_s":              (int,   "Seconds you can keep talking after it answers.", False),
    "wake_words":               (list,  "Spellings that wake it, for when speech mishears.", False),
    "custom_instructions":      (str,   "Standing instructions about how it should behave.", False),
    "llm.model":                (str,   "Ollama model. Bigger follows instructions better.", True),
    "llm.temperature":          (float, "0 is literal and repeatable, 1 is loose.", False),
    "stt.model_size":           (str,   "tiny, base, small, medium. Bigger hears better, slower.", True),
    "tts.rate":                 (int,   "Speaking speed, around 150-220.", False),
    "safety.confirm_dangerous": (bool,  "Ask out loud before deleting or killing things.", False),
}

CHOICES = {
    "language": ["en", "es", "auto"],
    "stt.model_size": ["tiny", "base", "small", "medium"],
}


def _dig(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _put(d, dotted, value):
    parts = dotted.split(".")
    for p in parts[:-1]:
        d = d.setdefault(p, {})
    d[parts[-1]] = value


def _merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def load(path="config.yaml") -> dict:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    try:
        if OVERRIDES.exists():
            _merge(cfg, json.loads(OVERRIDES.read_text(encoding="utf-8")))
    except Exception as e:
        log.warning("Ignoring unreadable overrides file: %s", e)
    cfg.setdefault("custom_instructions", "")
    return cfg


def coerce(name, value):
    """Turn whatever was typed or spoken into the right type, or explain why not."""
    kind = EDITABLE[name][0]
    if kind is bool:
        s = str(value).strip().lower()
        if s in ("true", "yes", "on", "1", "si", "sí"):
            return True
        if s in ("false", "no", "off", "0"):
            return False
        raise ValueError("expected yes or no")
    if kind is list:
        if isinstance(value, (list, tuple)):
            items = [str(x).strip().lower() for x in value]
        else:
            items = [x.strip().lower() for x in str(value).split(",")]
        items = [x for x in items if x]
        if not items:
            raise ValueError("needs at least one word")
        return items
    if kind in (int, float):
        try:
            return kind(float(str(value).strip()))
        except ValueError:
            raise ValueError(f"expected a number, got {value!r}")
    v = str(value).strip()
    if name in CHOICES and v not in CHOICES[name]:
        raise ValueError(f"must be one of: {', '.join(CHOICES[name])}")
    if not v and name != "custom_instructions":
        raise ValueError("cannot be empty")
    return v


def set_value(cfg, name, value):
    """Validate, save to the overlay, and apply to the live config.

    Returns (human message, needs_restart).
    """
    if name not in EDITABLE:
        raise KeyError(f"'{name}' is not a setting. Options: {', '.join(EDITABLE)}")
    clean = coerce(name, value)

    data = {}
    if OVERRIDES.exists():
        try:
            data = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    _put(data, name, clean)
    OVERRIDES.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    _put(cfg, name, clean)
    restart = EDITABLE[name][2]
    shown = clean if not isinstance(clean, str) or len(clean) < 60 else clean[:57] + "..."
    msg = f"{name} is now {shown}."
    if restart:
        msg += " That one takes effect next time Jarvis starts."
    return msg, restart


def reset(cfg_path="config.yaml"):
    """Throw away every override and go back to the shipped config."""
    if OVERRIDES.exists():
        OVERRIDES.unlink()
    return load(cfg_path)


def describe(cfg) -> str:
    out = []
    for name, (_, help_text, restart) in EDITABLE.items():
        val = _dig(cfg, name)
        if name == "custom_instructions":
            val = (val or "(none)")
            val = val if len(str(val)) < 70 else str(val)[:67] + "..."
        out.append(f"{name} = {val}" + ("  [needs restart]" if restart else ""))
    return "\n".join(out)
