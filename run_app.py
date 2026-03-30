"""
Wriggle Survey — Launcher
Checks license, then starts the Streamlit app.
"""
import sys
import os
import threading
import webbrowser
import time


def _open_browser():
    time.sleep(3)
    webbrowser.open("http://localhost:8501")


def main():
    # ── License check ─────────────────────────────────────────────────────────
    from license_manager import is_activated
    from license_dialog  import show_license_dialog

    if not is_activated():
        if not show_license_dialog():
            sys.exit(0)           # User closed dialog without valid key

    # ── Start Streamlit ───────────────────────────────────────────────────────
    threading.Thread(target=_open_browser, daemon=True).start()

    if getattr(sys, "frozen", False):
        # Running inside PyInstaller bundle
        os.chdir(sys._MEIPASS)

    import streamlit.web.cli as stcli
    sys.argv = [
        "streamlit", "run", "streamlit_app.py",
        "--server.headless=true",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
