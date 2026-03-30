"""
Wriggle Survey — Launcher
Checks license, then starts the Streamlit app.
"""
import sys
import os
import threading
import webbrowser
import time


def _patch_metadata():
    """
    PyInstaller strips package metadata — patch importlib.metadata.version
    so Streamlit can read its own version without crashing.
    """
    if not getattr(sys, "frozen", False):
        return
    import importlib.metadata as _meta
    _orig = _meta.version
    _FALLBACK = {
        "streamlit":   "1.40.0",
        "pandas":      "2.2.0",
        "numpy":       "1.26.0",
        "plotly":      "5.22.0",
        "matplotlib":  "3.8.0",
        "openpyxl":    "3.1.0",
        "altair":      "5.0.0",
        "pyarrow":     "14.0.0",
        "pydeck":      "0.8.0",
        "tornado":     "6.4.0",
        "click":       "8.1.0",
        "packaging":   "23.0",
        "PIL":         "10.0.0",
        "Pillow":      "10.0.0",
    }
    def _safe_version(name):
        try:
            return _orig(name)
        except _meta.PackageNotFoundError:
            if name in _FALLBACK:
                return _FALLBACK[name]
            raise
    _meta.version = _safe_version


def _free_port(preferred=8501):
    """Return preferred port if free, otherwise find a free one."""
    import socket
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


def _write_streamlit_config(port):
    """Write ~/.streamlit/config.toml to force developmentMode=false."""
    from pathlib import Path
    config_dir = Path.home() / ".streamlit"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.toml").write_text(
        "[global]\n"
        "developmentMode = false\n\n"
        "[server]\n"
        "headless = true\n"
        f"port = {port}\n"
        'fileWatcherType = "none"\n\n'
        "[browser]\n"
        "gatherUsageStats = false\n"
    )


def _open_browser(port=8501):
    time.sleep(4)
    webbrowser.open(f"http://localhost:{port}")


def main():
    # Must patch BEFORE any streamlit import
    _patch_metadata()

    # Write config.toml before Streamlit reads it
    port = _free_port(8501)
    _write_streamlit_config(port)

    # ── License check ─────────────────────────────────────────────────────────
    from license_manager import is_activated
    from license_dialog  import show_license_dialog

    if not is_activated():
        if not show_license_dialog():
            sys.exit(0)

    # ── Start Streamlit ───────────────────────────────────────────────────────
    threading.Thread(target=lambda: _open_browser(port), daemon=True).start()

    if getattr(sys, "frozen", False):
        os.chdir(sys._MEIPASS)

    import streamlit.web.cli as stcli
    sys.argv = ["streamlit", "run", "streamlit_app.py"]
    sys.exit(stcli.main())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        from pathlib import Path
        log = Path.home() / "WriggleSurvey_error.log"
        log.write_text(traceback.format_exc())
        print(f"HATA: {e}")
        print(f"Detay: {log}")
        input("Çıkmak için Enter'a basın...")
