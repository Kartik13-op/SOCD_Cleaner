# SOCD Cleaner (Python)

A software implementation of the Simultaneous Opposing Cardinal Directions (SOCD) resolution
mechanism found in high-end gaming keyboards. Intercepts raw keyboard input at the OS level
and applies last-input-wins logic to opposing directional key pairs.

---

## What is SOCD

SOCD stands for Simultaneous Opposing Cardinal Directions. It describes the situation where a
player presses two physically opposing keys at the same time — for example, A (left) and D (right)
on a standard WASD layout.

On a regular keyboard, pressing both keys together produces a neutral or cancelled state. The
game receives both signals and either stops the character or ignores the conflict entirely,
depending on the game engine. This is the default behavior everywhere.

SOCD resolution changes that. Instead of cancelling, the keyboard (or this script) applies a
rule to decide which key wins. The most common rule, and the one used here, is called
last-input-wins: whichever key was pressed most recently takes priority. The moment you tap D
while holding A, D becomes active and A is suppressed. Release D, and A immediately re-activates.
You never get a neutral state unless both keys are released.

This directly benefits counter-strafing in FPS games. The technique requires stopping your
movement before shooting to regain accuracy, which traditionally demands precise manual timing.
With SOCD resolution, the cancellation and re-activation happen at hardware speed rather than
depending on how quickly a player can lift a finger.

---

## Hardware That Does This

Several keyboards ship this as a built-in firmware feature. This script replicates the same
behavior entirely in software.

### Wooting (Rappy Snappy / Snappy Tappy)

Wooting keyboards, built around Hall-effect Lekker switches, were among the first to bring SOCD
resolution to gaming peripherals. Their implementation is called Rappy Snappy on the 60HE+ and
80HE models. It monitors selected key pairs and activates whichever key is pressed deepest (or
most recently, depending on mode). A related feature called Snappy Tappy applies similar logic
but with configurable behavior for how ties are resolved. Configuration is done through
Wootility, a browser-based tool that stores profiles on the keyboard itself.

Relevant models: Wooting 60HE+, Wooting 60HE v2, Wooting 80HE.

Reference: https://wooting.io/wooting-80he

### Razer (Snap Tap)

Razer introduced their equivalent feature, called Snap Tap, on the Huntsman V3 Pro lineup. It
functions on the same last-input-wins principle and is toggled through Razer Synapse. Razer was
notably one of the first major peripheral brands to bring this feature to a wider consumer market
after Wooting popularized it.

Reference: https://www.razer.com/gaming-keyboards/razer-huntsman-v3-pro

### SteelSeries (Rapid Tap)

SteelSeries released their version of the feature under the name Rapid Tap. It operates on the
same core principle and is available on select models in their analog keyboard lineup.

### Hit Box and Arcade Controllers

SOCD resolution originated in the fighting game community, specifically with leverless arcade
controllers like the Hit Box. These devices have no joystick — all directions are individual
buttons — which makes SOCD a hardware reality rather than an edge case. The FGC debated SOCD
rules for years before the keyboard market picked up the concept.

---

## How This Script Works

```
Hold A          -> stack: [A]       -> A is active
Hold D          -> stack: [A, D]    -> D wins, A suppressed
Release D       -> stack: [A]       -> A re-activates
Release A       -> stack: []        -> nothing active
```

The script intercepts all key events using pynput's suppress mode, meaning the OS never sees
the raw input. Instead, the script decides what to forward through a virtual controller. Each
configured key pair maintains an ordered stack of currently-held keys. The last key in the stack
is always the active one. When the top key is released, the next key in the stack fires
automatically.

---

## Setup

Install the only dependency:

```
pip install pynput
```

Run the script:

```
python socd_cleaner.py
```

Press ESC to stop.

### Platform Notes

- Windows: works without elevated permissions in most cases.
- macOS: requires Accessibility access. Go to System Settings -> Privacy and Security ->
  Accessibility and add your terminal or Python executable.
- Linux: may require running with sudo, or add your user to the input group:
  `sudo usermod -aG input $USER` then log out and back in.

---

## Configuring Key Pairs

At the top of socd_cleaner.py, edit the SOCD_PAIRS list:

```python
SOCD_PAIRS = [
    ('a', 'd'),   # horizontal
    ('w', 's'),   # vertical
]
```

You can add arrow keys or any other pair:

```python
from pynput.keyboard import Key

SOCD_PAIRS = [
    ('a', 'd'),
    ('w', 's'),
    (Key.left, Key.right),
    (Key.up,   Key.down),
]
```

---

## Anti-Cheat Risks

This is the most important section if you intend to use this script while playing online games
with active anti-cheat software.

### Why software SOCD is riskier than hardware SOCD

Hardware SOCD resolvers (Wooting, Razer) operate at the firmware level inside the keyboard itself.
From the perspective of the operating system and any software running on it, the keyboard simply
never sends conflicting inputs. The OS only ever sees one direction at a time. No process on your
PC can detect the resolution happening because it is invisible at the OS boundary.

This script works differently. It runs as a user-mode process on your PC, intercepts keyboard
events, and re-emits them through a virtual input device. Anti-cheat software that monitors
running processes, input driver behavior, or virtual device creation can potentially see this
activity.

### Known bans and restrictions by game

Counter-Strike 2 (Valve / VAC Live):
Valve explicitly banned hardware-assisted SOCD resolution in August 2024. Wooting's own
documentation warns players to disable Snappy Tappy and Rappy Snappy before queuing on Valve
servers, as using them results in a match kick. A software implementation running as a separate
process on the same machine carries significantly more detection risk than a hardware-level
implementation that Valve already moved to block. Using this script in CS2 is not recommended.

Valorant (Riot / Vanguard):
Vanguard is a kernel-level anti-cheat that loads at Windows boot and runs continuously. It
monitors processes, loaded drivers, and input behavior at a deeper level than most other
anti-cheats. A process that intercepts and re-emits keyboard input through a virtual controller
is the kind of behavior kernel-level systems are designed to detect. The risk of a ban or flag
in Valorant with this script running is real and should be taken seriously. Disable and exit
the script before launching Valorant.

Fortnite (Epic / Easy Anti-Cheat):
EAC uses behavioral fingerprinting and process monitoring. The SOCD feature itself is not
explicitly banned in Fortnite, and Epic has historically incorporated movement features rather
than blocking them (they added analog-style movement natively after Wooting's Double Movement
tool became popular). However, a third-party process intercepting input remains a potential flag.
Use with caution and check current Epic terms before using in ranked modes.

Apex Legends (EA / Easy Anti-Cheat):
Similar risk profile to Fortnite. EAC is the underlying system. No specific ruling against SOCD
has been publicly issued for Apex, but the process behavior this script exhibits is not exempt
from scrutiny.

### General rule

If a game uses a kernel-level anti-cheat (Vanguard, EAC, BattlEye), treat any software that
intercepts or re-emits input as a potential ban risk, regardless of whether the feature itself
has been explicitly called out. These systems are designed to flag unusual input-layer behavior,
not just known cheat signatures.

Hardware SOCD from a Wooting or Razer keyboard is safer in this respect because the resolution
is invisible to software running on the host machine. A Python script doing the same thing is
not invisible.

### Safe use cases

- Offline games with no anti-cheat.
- Games with user-mode or server-side only anti-cheat where no explicit ruling exists.
- Local testing, game development, or accessibility tooling.
- Any game that explicitly permits SOCD software or has built the feature into the game itself.

---

## References

- Wooting SOCD (Rappy Snappy): https://wooting.io/wooting-80he
- Wooting CS2 guide and Valve SOCD ban notice: https://wooting.io/post/wooting-cs2-guide-in-game-benefits-rapid-trigger-settings-and-pro-profiles
- Razer Snap Tap overview: https://www.pcgamer.com/hardware/gaming-keyboards/what-is-socd-snap-tap/
- SOCD vs Rapid Trigger technical breakdown: https://attackshark.com/blogs/knowledges/socd-rapid-trigger-game-fairness-performance
- pynput documentation: https://pynput.readthedocs.io

---
