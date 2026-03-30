"""
Wriggle Survey — License Key Dialog (Tkinter)
"""
import tkinter as tk
from tkinter import messagebox
from license_manager import validate_key, save_activation


def show_license_dialog() -> bool:
    """
    Display a license activation window.
    Returns True if a valid key was entered and saved.
    """
    result = {"ok": False}

    root = tk.Tk()
    root.title("Wriggle Survey — Lisans Aktivasyonu")
    root.geometry("460x260")
    root.resizable(False, False)
    root.configure(bg="#1a1a2e")

    # Centre on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth()  - 460) // 2
    y = (root.winfo_screenheight() - 260) // 2
    root.geometry(f"460x260+{x}+{y}")

    # ── Header ──────────────────────────────────────────────────────────────
    tk.Label(root, text="⭕  Wriggle Survey",
             bg="#1a1a2e", fg="#ffffff",
             font=("Segoe UI", 16, "bold")).pack(pady=(28, 2))

    tk.Label(root, text="Best-Fit Circle 3D  —  Kasa Method",
             bg="#1a1a2e", fg="#94a3b8",
             font=("Segoe UI", 9)).pack()

    tk.Label(root, text="Lisans anahtarınızı girin:",
             bg="#1a1a2e", fg="#cbd5e1",
             font=("Segoe UI", 10)).pack(pady=(18, 6))

    # ── Entry ────────────────────────────────────────────────────────────────
    entry_var = tk.StringVar()
    entry = tk.Entry(root, textvariable=entry_var,
                     font=("Courier New", 13), width=24, justify="center",
                     bg="#0f172a", fg="#e2e8f0",
                     insertbackground="#e2e8f0",
                     relief="flat", bd=6)
    entry.pack(ipady=4)
    entry.insert(0, "WRS-XXXXX-XXXXX-XXXXX")
    entry.select_range(0, tk.END)
    entry.focus_set()

    # ── Activate button ───────────────────────────────────────────────────────
    def on_activate(_event=None):
        key = entry_var.get().strip()
        if validate_key(key):
            save_activation(key)
            result["ok"] = True
            root.destroy()
        else:
            messagebox.showerror(
                "Geçersiz Lisans",
                "❌  Lisans anahtarı geçersiz!\n\nLütfen size verilen anahtarı doğru girin.",
                parent=root,
            )
            entry.select_range(0, tk.END)
            entry.focus_set()

    tk.Button(root, text="  Etkinleştir  ",
              command=on_activate,
              bg="#1d4ed8", fg="white",
              activebackground="#2563eb", activeforeground="white",
              font=("Segoe UI", 11, "bold"),
              relief="flat", cursor="hand2",
              padx=14, pady=6).pack(pady=18)

    root.bind("<Return>", on_activate)
    root.protocol("WM_DELETE_WINDOW", root.destroy)   # X butonu → çıkış
    root.mainloop()

    return result["ok"]
