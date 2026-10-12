"""Jarvis - offline voice assistant. Entry point.

Default        : opens the control window (plus a system-tray icon).
--headless     : no window, runs invisibly in the background.

Only one copy runs at a time. Launching it again does not start a second
one - it tells the copy that is already running to show its window.
"""
import logging
import os
import socket
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

import settings as settings_mod

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
(ROOT / "data").mkdir(exist_ok=True)

handlers = [RotatingFileHandler(ROOT / "data" / "jarvis.log", maxBytes=2_000_000,
                                backupCount=3, encoding="utf-8")]
if sys.stdout:                      # pythonw has no console
    handlers.append(logging.StreamHandler(sys.stdout))
logging.basicConfig(level=logging.INFO, handlers=handlers,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("jarvis")

PORT = 47821                        # loopback only; doubles as the single-instance lock


def claim_instance():
    """Return a bound socket, or None if Jarvis is already running.

    When another copy holds the port we poke it so it pops its window up,
    which is what the user wanted by launching the app again.
    """
    s = socket.socket()
    # On Windows SO_REUSEADDR lets a SECOND process bind the same port, which would
    # defeat the whole point. SO_EXCLUSIVEADDRUSE is the correct flag there.
    if os.name == "nt":
        s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        # Elsewhere SO_REUSEADDR only skips the TIME_WAIT delay after a restart;
        # it still will not allow a second live listener.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", PORT))
        s.listen(4)
        return s
    except OSError:
        pass
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=3) as c:
            c.sendall(b"show")
        log.info("Jarvis was already running - asked it to show its window.")
        print("Jarvis is already running. Its window should be in front now.")
    except OSError as e:
        log.warning("Another copy holds the port but will not answer: %s", e)
        print("Jarvis seems to be running but is not responding. Run STOP_JARVIS.bat, then try again.")
    return None


def serve_show_requests(sock, on_show):
    """Watch for other launches asking us to surface the window."""
    def loop():
        while True:
            try:
                conn, _ = sock.accept()
            except OSError:
                return
            with conn:
                try:
                    conn.recv(16)
                except OSError:
                    pass
            try:
                on_show()
            except Exception:
                log.exception("Could not show the window")
    threading.Thread(target=loop, name="jarvis-ipc", daemon=True).start()


def main():
    lock = claim_instance()
    if lock is None:
        return
    cfg = settings_mod.load(ROOT / "config.yaml")

    if "--headless" in sys.argv:
        import assistant
        a = assistant.Assistant(
            cfg,
            on_event=lambda kind, text: log.info("%s: %s", kind.upper(), text),
            on_status=lambda s: log.info("STATUS: %s", s),
        )
        serve_show_requests(lock, lambda: None)
        a.start()
        a._thread.join()
        return

    from gui import JarvisApp
    app = JarvisApp(cfg)
    serve_show_requests(lock, app.show)
    app.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Fatal error")
        raise
