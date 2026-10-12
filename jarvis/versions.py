"""Version snapshots for Jarvis - save, list and roll back, with no git needed.

Every snapshot is a dated zip in versions/. Restoring puts the code back exactly
as it was, and takes a safety snapshot of the current state first, so a restore
is itself undoable. Your environment (.venv) and the voice model are never
touched - only the code and settings.
"""
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "versions"
SKIP_DIRS = {".venv", "versions", "__pycache__", ".git", "voices"}
SKIP_FILES = {"jarvis.log"}


def files_to_save():
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.name in SKIP_FILES or p.name.startswith("jarvis.log"):
            continue
        yield p, rel


def save(label=""):
    STORE.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    clean = "".join(c for c in label if c.isalnum() or c in " -_").strip().replace(" ", "-")
    name = f"{stamp}{'_' + clean if clean else ''}.zip"
    out = STORE / name
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p, rel in files_to_save():
            z.write(p, rel.as_posix())
            n += 1
    size = out.stat().st_size / 1024
    print(f"\n  Saved: {name}")
    print(f"  {n} files, {size:.0f} KB\n")
    return out


def listing():
    STORE.mkdir(exist_ok=True)
    zips = sorted(STORE.glob("*.zip"), reverse=True)
    if not zips:
        print("\n  No versions saved yet.\n")
        return []
    print()
    for i, z in enumerate(zips, start=1):
        when = datetime.fromtimestamp(z.stat().st_mtime).strftime("%d %b %Y, %H:%M")
        print(f"  [{i}]  {z.stem:<34} {when}")
    print()
    return zips


def restore(zips):
    if not zips:
        return
    try:
        pick = int(input("  Restore which number? (0 to cancel): ").strip() or "0")
    except ValueError:
        print("  Not a number.")
        return
    if not 1 <= pick <= len(zips):
        print("  Cancelled.")
        return
    chosen = zips[pick - 1]
    print(f"\n  About to restore: {chosen.stem}")
    if input("  Type yes to confirm: ").strip().lower() not in ("yes", "y"):
        print("  Cancelled.")
        return

    print("  Taking a safety snapshot of the current state first...")
    save("before-restore")

    with zipfile.ZipFile(chosen) as z:
        z.extractall(ROOT)
    print(f"\n  Restored {chosen.stem}.")
    print("  Run STOP_JARVIS.bat, then open Jarvis again.\n")


def main():
    print("=" * 58)
    print("  JARVIS VERSIONS")
    print("=" * 58)
    print("\n  1  Save the current version")
    print("  2  List saved versions")
    print("  3  Roll back to a saved version")
    print("  0  Close\n")
    choice = input("  Choose: ").strip()
    if choice == "1":
        save(input("  Short label (optional, e.g. 'before my edits'): ").strip())
    elif choice == "2":
        listing()
    elif choice == "3":
        restore(listing())
    input("  Press Enter to close")


if __name__ == "__main__":
    main()
