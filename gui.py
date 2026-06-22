"""
SOCD Cleaner - GUI
===================
CustomTkinter front-end for SOCDCleaner.

Requirements:
  pip install pynput customtkinter

Usage:
  python gui.py
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from socd_cleaner import SOCDCleaner


# ── Theme ─────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Palette
CLR_BG       = "#0f1117"
CLR_SURFACE  = "#1a1d27"
CLR_CARD     = "#21253a"
CLR_BORDER   = "#2e3250"
CLR_ACCENT   = "#4f6ef7"
CLR_ACCENT_H = "#6b85ff"
CLR_STOP     = "#e05c5c"
CLR_STOP_H   = "#f07070"
CLR_SUCCESS  = "#3ecf8e"
CLR_TEXT     = "#e8eaf6"
CLR_MUTED    = "#7b82a8"
CLR_BADGE_ON = "#1a3a2a"
CLR_BADGE_OFF= "#2a1a1a"


# ── Pair row widget ───────────────────────────────────────────────────────────

class PairRow(ctk.CTkFrame):
    """A single key-pair row with two entry fields and a remove button."""

    def __init__(self, master, key_a: str = "a", key_b: str = "d",
                 on_remove=None, **kwargs):
        super().__init__(master, fg_color=CLR_CARD,
                         corner_radius=8, **kwargs)
        self._on_remove = on_remove

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=0)

        entry_cfg = dict(
            width=72, height=36,
            fg_color=CLR_SURFACE,
            border_color=CLR_BORDER,
            border_width=1,
            text_color=CLR_TEXT,
            font=ctk.CTkFont(family="Courier New", size=15, weight="bold"),
            justify="center",
            corner_radius=6,
        )

        self._var_a = tk.StringVar(value=key_a)
        self._var_b = tk.StringVar(value=key_b)

        self._entry_a = ctk.CTkEntry(self, textvariable=self._var_a, **entry_cfg)
        self._entry_a.grid(row=0, column=0, padx=(12, 0), pady=10, sticky="ew")

        ctk.CTkLabel(self, text="vs", font=ctk.CTkFont(size=12),
                     text_color=CLR_MUTED).grid(row=0, column=1, padx=10)

        self._entry_b = ctk.CTkEntry(self, textvariable=self._var_b, **entry_cfg)
        self._entry_b.grid(row=0, column=2, padx=(0, 0), pady=10, sticky="ew")

        self._btn_remove = ctk.CTkButton(
            self, text="✕", width=32, height=32,
            fg_color="transparent", hover_color=CLR_BORDER,
            text_color=CLR_MUTED, font=ctk.CTkFont(size=13),
            corner_radius=6,
            command=self._remove,
        )
        self._btn_remove.grid(row=0, column=3, padx=(6, 8))

    def get_pair(self) -> tuple[str, str] | None:
        """Return (a, b) or None if either field is blank."""
        a = self._var_a.get().strip().lower()
        b = self._var_b.get().strip().lower()
        if not a or not b:
            return None
        return a, b

    def lock(self) -> None:
        self._entry_a.configure(state="disabled")
        self._entry_b.configure(state="disabled")
        self._btn_remove.configure(state="disabled")

    def unlock(self) -> None:
        self._entry_a.configure(state="normal")
        self._entry_b.configure(state="normal")
        self._btn_remove.configure(state="normal")

    def _remove(self) -> None:
        if self._on_remove:
            self._on_remove(self)


# ── Main app window ───────────────────────────────────────────────────────────

class SOCDApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("SOCD Cleaner")
        self.geometry("420x560")
        self.minsize(380, 480)
        self.resizable(True, True)
        self.configure(fg_color=CLR_BG)

        self._cleaner: SOCDCleaner | None = None
        self._pair_rows: list[PairRow] = []

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ── Header ──
        header = ctk.CTkFrame(self, fg_color=CLR_SURFACE,
                              corner_radius=0, height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=20, pady=12, sticky="w")

        ctk.CTkLabel(
            title_frame, text="SOCD Cleaner",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=CLR_TEXT,
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame, text="  last-input-wins",
            font=ctk.CTkFont(size=11),
            text_color=CLR_MUTED,
        ).pack(side="left", pady=(4, 0))

        # Status badge (top-right)
        self._badge_var = tk.StringVar(value="INACTIVE")
        self._badge = ctk.CTkLabel(
            header,
            textvariable=self._badge_var,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=CLR_STOP,
            fg_color=CLR_BADGE_OFF,
            corner_radius=6,
            width=70, height=24,
        )
        self._badge.grid(row=0, column=1, padx=16, pady=12, sticky="e")
        header.columnconfigure(1, weight=0)

        # ── Pairs section ──
        pairs_card = ctk.CTkFrame(self, fg_color=CLR_SURFACE, corner_radius=12)
        pairs_card.grid(row=1, column=0, padx=16, pady=(16, 0), sticky="ew")
        pairs_card.columnconfigure(0, weight=1)

        label_row = ctk.CTkFrame(pairs_card, fg_color="transparent")
        label_row.grid(row=0, column=0, padx=16, pady=(14, 6), sticky="ew")
        label_row.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            label_row, text="Key Pairs",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=CLR_TEXT,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            label_row, text="opposing direction keys",
            font=ctk.CTkFont(size=11),
            text_color=CLR_MUTED,
        ).grid(row=0, column=1, sticky="e")

        # Scrollable container for pair rows
        self._pairs_frame = ctk.CTkScrollableFrame(
            pairs_card, fg_color="transparent",
            scrollbar_button_color=CLR_BORDER,
            scrollbar_button_hover_color=CLR_ACCENT,
            height=180,
        )
        self._pairs_frame.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="ew")
        self._pairs_frame.columnconfigure(0, weight=1)

        # Default pairs
        self._add_pair_row("a", "d")
        self._add_pair_row("w", "s")

        # Add pair button
        self._btn_add = ctk.CTkButton(
            pairs_card,
            text="+ Add Pair",
            height=32,
            fg_color="transparent",
            hover_color=CLR_CARD,
            border_width=1,
            border_color=CLR_BORDER,
            text_color=CLR_MUTED,
            font=ctk.CTkFont(size=12),
            corner_radius=8,
            command=self._add_pair_row,
        )
        self._btn_add.grid(row=2, column=0, padx=16, pady=(0, 14), sticky="ew")

        # ── Log box ──
        log_card = ctk.CTkFrame(self, fg_color=CLR_SURFACE, corner_radius=12)
        log_card.grid(row=2, column=0, padx=16, pady=(12, 0), sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            log_card, text="Activity Log",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=CLR_MUTED,
        ).grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")

        self._log = ctk.CTkTextbox(
            log_card,
            fg_color=CLR_BG,
            text_color=CLR_TEXT,
            font=ctk.CTkFont(family="Courier New", size=11),
            border_width=0,
            corner_radius=8,
            wrap="word",
            state="disabled",
        )
        self._log.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # ── Control buttons ──
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=3, column=0, padx=16, pady=14, sticky="ew")
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        self._btn_start = ctk.CTkButton(
            btn_row,
            text="Start",
            height=44,
            fg_color=CLR_ACCENT,
            hover_color=CLR_ACCENT_H,
            text_color="#ffffff",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10,
            command=self._on_start,
        )
        self._btn_start.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self._btn_stop = ctk.CTkButton(
            btn_row,
            text="Stop",
            height=44,
            fg_color=CLR_SURFACE,
            hover_color=CLR_STOP_H,
            border_width=1,
            border_color=CLR_BORDER,
            text_color=CLR_MUTED,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10,
            state="disabled",
            command=self._on_stop,
        )
        self._btn_stop.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    # ── Pair management ───────────────────────────────────────────────────────

    def _add_pair_row(self, key_a: str = "", key_b: str = "") -> None:
        row = PairRow(
            self._pairs_frame,
            key_a=key_a, key_b=key_b,
            on_remove=self._remove_pair_row,
        )
        row.grid(
            row=len(self._pair_rows), column=0,
            padx=4, pady=4, sticky="ew",
        )
        self._pair_rows.append(row)

    def _remove_pair_row(self, row: PairRow) -> None:
        if len(self._pair_rows) <= 1:
            self._log_message("At least one key pair is required.")
            return
        row.grid_forget()
        row.destroy()
        self._pair_rows.remove(row)
        # Re-grid remaining rows
        for i, r in enumerate(self._pair_rows):
            r.grid(row=i, column=0, padx=4, pady=4, sticky="ew")

    def _collect_pairs(self) -> list[tuple] | None:
        """Collect and validate all pair rows. Returns None on error."""
        pairs = []
        for row in self._pair_rows:
            pair = row.get_pair()
            if pair is None:
                messagebox.showerror(
                    "Invalid pair",
                    "Each pair needs two non-empty keys."
                )
                return None
            if pair[0] == pair[1]:
                messagebox.showerror(
                    "Invalid pair",
                    f"A pair cannot use the same key twice: '{pair[0]}'"
                )
                return None
            pairs.append(pair)
        return pairs

    # ── Start / Stop ──────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        pairs = self._collect_pairs()
        if not pairs:
            return

        self._cleaner = SOCDCleaner(
            pairs=pairs,
            on_status_change=self._on_cleaner_status,
        )

        try:
            self._cleaner.start()
        except Exception as e:
            messagebox.showerror("Failed to start", str(e))
            self._cleaner = None
            return

        self._lock_ui()

        pairs_txt = ", ".join(f"{a}:{b}" for a, b in pairs)
        self._log_message(f"Started  --  pairs: {pairs_txt}")

    def _on_stop(self) -> None:
        if self._cleaner:
            self._cleaner.stop()
            self._cleaner = None
        self._unlock_ui()
        self._log_message("Stopped.")

    # ── Status callback (runs on cleaner thread) ──────────────────────────────

    def _on_cleaner_status(self, active: bool) -> None:
        self.after(0, self._apply_status, active)

    def _apply_status(self, active: bool) -> None:
        if active:
            self._badge_var.set("ACTIVE")
            self._badge.configure(text_color=CLR_SUCCESS, fg_color=CLR_BADGE_ON)
        else:
            self._badge_var.set("INACTIVE")
            self._badge.configure(text_color=CLR_STOP, fg_color=CLR_BADGE_OFF)

    # ── UI lock helpers ───────────────────────────────────────────────────────

    def _lock_ui(self) -> None:
        for row in self._pair_rows:
            row.lock()
        self._btn_add.configure(state="disabled")
        self._btn_start.configure(state="disabled")
        self._btn_stop.configure(
            state="normal",
            fg_color=CLR_STOP,
            hover_color=CLR_STOP_H,
            text_color="#ffffff",
            border_width=0,
        )

    def _unlock_ui(self) -> None:
        for row in self._pair_rows:
            row.unlock()
        self._btn_add.configure(state="normal")
        self._btn_start.configure(state="normal")
        self._btn_stop.configure(
            state="disabled",
            fg_color=CLR_SURFACE,
            hover_color=CLR_STOP_H,
            text_color=CLR_MUTED,
            border_width=1,
        )

    # ── Log ───────────────────────────────────────────────────────────────────

    def _log_message(self, msg: str) -> None:
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._log.configure(state="normal")
        self._log.insert("end", f"[{ts}]  {msg}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    # ── Window close ─────────────────────────────────────────────────────────

    def on_close(self) -> None:
        if self._cleaner and self._cleaner.running:
            self._cleaner.stop()
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = SOCDApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
