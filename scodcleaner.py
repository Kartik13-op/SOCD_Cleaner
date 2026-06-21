from pynput import keyboard
from pynput.keyboard import Key, KeyCode, Controller
import threading

# ── Key pairs to manage (opposing axis pairs) ────────────────────────────────
# Each tuple is (negative_direction_key, positive_direction_key)
SOCD_PAIRS = [
    ('a', 'd'),   # Horizontal: left / right
    ('w', 's'),   # Vertical:   up   / down
    # Add more pairs here if needed, e.g.:
    # (Key.left, Key.right),
    # (Key.up,   Key.down),
]

# ── Internal state ────────────────────────────────────────────────────────────
controller = Controller()

# For each axis, keep an ordered stack of currently-held keys.
# The LAST element is always the "active" (winning) key.
# Structure: { frozenset({keyA, keyB}): [ordered list of held keys] }
axis_stacks: dict[frozenset, list] = {}
axis_map:    dict                  = {}   # key -> its axis frozenset

# Which keys are currently being virtually suppressed
suppressed: set = set()
lock = threading.Lock()


def _normalise(key) -> str | Key:
    """Return a comparable, hashable form of a key."""
    if isinstance(key, KeyCode):
        return key.char.lower() if key.char else key
    return key


def _setup_axes():
    for pair in SOCD_PAIRS:
        a, b = pair
        axis = frozenset({a, b})
        axis_stacks[axis] = []
        axis_map[a] = axis
        axis_map[b] = axis


def _active_key(axis: frozenset):
    """Return the currently winning key for this axis, or None."""
    stack = axis_stacks[axis]
    return stack[-1] if stack else None


def _press_virtual(key):
    """Send a key-down event via the virtual controller."""
    try:
        controller.press(key)
    except Exception:
        pass


def _release_virtual(key):
    """Send a key-up event via the virtual controller."""
    try:
        controller.release(key)
    except Exception:
        pass


def on_press(key):
    key = _normalise(key)

    # ESC exits
    if key == Key.esc:
        return False   # stops the listener

    with lock:
        if key not in axis_map:
            return True   # not an SOCD key — pass through normally

        axis  = axis_map[key]
        stack = axis_stacks[axis]

        if key in stack:
            return False  # already tracked, suppress duplicate

        prev_active = _active_key(axis)
        stack.append(key)
        new_active = _active_key(axis)

        if prev_active is not None and prev_active != new_active:
            # Suppress the old winner
            suppressed.add(prev_active)
            _release_virtual(prev_active)

        # Press the new winner
        suppressed.discard(new_active)
        _press_virtual(new_active)

    return False   # suppress original event; we handle it ourselves


def on_release(key):
    key = _normalise(key)

    with lock:
        if key not in axis_map:
            return True

        axis  = axis_map[key]
        stack = axis_stacks[axis]

        if key not in stack:
            return True   # wasn't tracked

        was_active = _active_key(axis)
        stack.remove(key)
        now_active = _active_key(axis)

        if key == was_active:
            # The winner was released
            _release_virtual(key)
            suppressed.discard(key)

            if now_active is not None:
                # Re-activate the previously suppressed key
                suppressed.discard(now_active)
                _press_virtual(now_active)
        else:
            # A suppressed key was released — just remove from stack, no event
            suppressed.discard(key)

    return False


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _setup_axes()

    pairs_display = ", ".join(f"'{a}' vs '{b}'" for a, b in SOCD_PAIRS)
    print("=" * 55)
    print("  SOCD Cleaner — Last Input Wins")
    print("=" * 55)
    print(f"  Managed pairs : {pairs_display}")
    print("  Resolution    : Last key pressed wins")
    print("  Stop          : Press ESC")
    print("=" * 55)
    print()
    print("  Example:")
    print("    Hold A  →  moving left")
    print("    Hold D  →  A cancelled, moving right  (last wins)")
    print("    Release D  →  A re-activates, moving left again")
    print()

    with keyboard.Listener(
        on_press=on_press,
        on_release=on_release,
        suppress=True          # intercept ALL key events so we control output
    ) as listener:
        listener.join()

    print("\n  SOCD Cleaner stopped.")
