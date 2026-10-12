"""Long-term facts Jarvis remembers between reboots (stored locally as JSON)."""
import json
import threading
from pathlib import Path


class Memory:
    def __init__(self, cfg):
        self.path = Path(cfg["memory"]["file"])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.facts: list[str] = []
        if self.path.exists():
            try:
                self.facts = json.loads(self.path.read_text(encoding="utf-8")).get("facts", [])
            except Exception:
                self.facts = []

    def add(self, fact: str) -> str:
        with self._lock:
            if fact not in self.facts:
                self.facts.append(fact)
                self._save()
        return "Saved."

    def remove(self, text: str) -> str:
        with self._lock:
            before = len(self.facts)
            self.facts = [f for f in self.facts if text.lower() not in f.lower()]
            self._save()
        return f"Removed {before - len(self.facts)} fact(s)."

    def _save(self):
        self.path.write_text(json.dumps({"facts": self.facts}, ensure_ascii=False, indent=2), encoding="utf-8")

    def as_text(self) -> str:
        return "\n".join(f"- {f}" for f in self.facts) or "(nothing yet)"
