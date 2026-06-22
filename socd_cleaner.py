"""
SOCD Cleaner - Last Input Wins
================================
Simulates the "Wooting-style" SOCD (Simultaneous Opposing Cardinal Directions)
resolution in Python. When two opposing keys are held (e.g. A + D), the most
recently pressed key wins. When the newer key is released, the older one
re-activates — just like a hardware SOCD cleaner.

How it works:
  - Intercepts raw key events via `pynput`
  - Tracks a stack per axis (Horizontal: A/D, Vertical: W/S)
  - Suppresses the "losing" key from being passed to the OS/game
  - When the top-of-stack key is released, the next key in the stack re-fires

Requirements:
  pip install pynput

Usage:
  Instantiate SOCDCleaner, call .start() and .stop().
  Or run this file directly for a CLI demo.

Note:
  On Linux you may need to run with sudo, or add your user to the 'input' group.
  On macOS you need to grant Accessibility permissions in System Preferences.
  On Windows it should work out of the box.
"""

from __future__ import annotations

import threading
from typing import Callable

from pynput import keyboard
from pynput.keyboard import Key, KeyCode, Controller


class SOCDCleaner:
    """
    Software SOCD resolver using last-input-wins logic.

    Parameters
    ----------
    pairs : list[tuple]
        List of (key_a, key_b) opposing pairs to manage.
        Keys can be single-character strings ('a', 'd') or pynput Key values.
    on_status_change : Callable[[bool], None] | None
        Optional callback fired whenever the cleaner starts or stops.
        Receives True when active, False when stopped.
    """

    def __init__(
        self,
        pairs: list[tuple] | None = None,
        on_status_change: Callable[[bool], None] | None = None,
    ):
        self._pairs: list[tuple] = pairs or [("a", "d"), ("w", "s")]
        self._on_status_change = on_status_change

        self._controller = Controller()
        self._lock = threading.Lock()
        self._listener: keyboard.Listener | None = None
        self._running = False

        # Per-axis state
        self._axis_stacks: dict[frozenset, list] = {}
        self._axis_map: dict = {}
        self._suppressed: set = set()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._running

    def set_pairs(self, pairs: list[tuple]) -> None:
        """
        Replace the managed key pairs. Takes effect on the next .start() call.
        Call .stop() then .start() to apply mid-session.
        """
        if self._running:
            raise RuntimeError("Stop the cleaner before changing pairs.")
        self._pairs = pairs

    def start(self) -> None:
        """Start intercepting keyboard input."""
        if self._running:
            return
        self._build_axes()
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=True,
        )
        self._listener.start()
        self._running = True
        if self._on_status_change:
            self._on_status_change(True)

    def stop(self) -> None:
        """Stop intercepting keyboard input and release any held virtual keys."""
        if not self._running:
            return
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._flush_virtual_keys()
        self._clear_state()
        if self._on_status_change:
            self._on_status_change(False)

    # ── Internal setup ────────────────────────────────────────────────────────

    def _build_axes(self) -> None:
        self._axis_stacks = {}
        self._axis_map = {}
        self._suppressed = set()
        for pair in self._pairs:
            a, b = self._normalise(pair[0]), self._normalise(pair[1])
            axis = frozenset({a, b})
            self._axis_stacks[axis] = []
            self._axis_map[a] = axis
            self._axis_map[b] = axis

    def _clear_state(self) -> None:
        self._axis_stacks = {}
        self._axis_map = {}
        self._suppressed = set()

    def _flush_virtual_keys(self) -> None:
        """Release any keys that are currently held virtually."""
        with self._lock:
            for axis, stack in self._axis_stacks.items():
                if stack:
                    self._release_virtual(stack[-1])
            self._suppressed.clear()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _normalise(key) -> str | Key:
        """Return a comparable, hashable form of a key."""
        if isinstance(key, KeyCode):
            return key.char.lower() if key.char else key
        if isinstance(key, str):
            return key.lower()
        return key

    def _active_key(self, axis: frozenset):
        stack = self._axis_stacks[axis]
        return stack[-1] if stack else None

    def _press_virtual(self, key) -> None:
        try:
            self._controller.press(key)
        except Exception:
            pass

    def _release_virtual(self, key) -> None:
        try:
            self._controller.release(key)
        except Exception:
            pass

    # ── Listener callbacks ────────────────────────────────────────────────────

    def _on_press(self, key) -> bool | None:
        key = self._normalise(key)

        with self._lock:
            if key not in self._axis_map:
                return True  # not managed — pass through

            axis = self._axis_map[key]
            stack = self._axis_stacks[axis]

            if key in stack:
                return False  # duplicate press, suppress

            prev_active = self._active_key(axis)
            stack.append(key)
            new_active = self._active_key(axis)

            if prev_active is not None and prev_active != new_active:
                self._suppressed.add(prev_active)
                self._release_virtual(prev_active)

            self._suppressed.discard(new_active)
            self._press_virtual(new_active)

        return False  # suppress original event

    def _on_release(self, key) -> bool | None:
        key = self._normalise(key)

        with self._lock:
            if key not in self._axis_map:
                return True

            axis = self._axis_map[key]
            stack = self._axis_stacks[axis]

            if key not in stack:
                return True

            was_active = self._active_key(axis)
            stack.remove(key)
            now_active = self._active_key(axis)

            if key == was_active:
                self._release_virtual(key)
                self._suppressed.discard(key)
                if now_active is not None:
                    self._suppressed.discard(now_active)
                    self._press_virtual(now_active)
            else:
                self._suppressed.discard(key)

        return False


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import signal
    import sys

    stop_event = threading.Event()

    def _handle_signal(sig, frame):
        print("\n  Stopping SOCD Cleaner...")
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    cleaner = SOCDCleaner(
        pairs=[("a", "d"), ("w", "s")],
        on_status_change=lambda active: print(
            f"  SOCD Cleaner {'started' if active else 'stopped'}."
        ),
    )

    print("=" * 55)
    print("  SOCD Cleaner -- Last Input Wins")
    print("=" * 55)
    print("  Managed pairs : 'a' vs 'd',  'w' vs 's'")
    print("  Resolution    : Last key pressed wins")
    print("  Stop          : Ctrl+C")
    print("=" * 55)

    cleaner.start()
    stop_event.wait()
    cleaner.stop()
    sys.exit(0)
