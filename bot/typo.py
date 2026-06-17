"""
Typo Engine — Human-like typo simulation for stealth.

Introduces a configurable chance (default 5%) of sending a mistyped command
first, followed by the corrected version after a brief "oops" delay.
Typos are generated using QWERTY keyboard adjacency so they look realistic.
"""

import random
import asyncio
from bot.hud import HUD, logger

# ─── QWERTY Keyboard Adjacency Map ───
# Each key maps to its immediate neighbors on a standard QWERTY layout.
QWERTY_NEIGHBORS = {
    'q': ['w', 'a'],
    'w': ['q', 'e', 'a', 's'],
    'e': ['w', 'r', 's', 'd'],
    'r': ['e', 't', 'd', 'f'],
    't': ['r', 'y', 'f', 'g'],
    'y': ['t', 'u', 'g', 'h'],
    'u': ['y', 'i', 'h', 'j'],
    'i': ['u', 'o', 'j', 'k'],
    'o': ['i', 'p', 'k', 'l'],
    'p': ['o', 'l'],
    'a': ['q', 'w', 's', 'z'],
    's': ['w', 'e', 'a', 'd', 'z', 'x'],
    'd': ['e', 'r', 's', 'f', 'x', 'c'],
    'f': ['r', 't', 'd', 'g', 'c', 'v'],
    'g': ['t', 'y', 'f', 'h', 'v', 'b'],
    'h': ['y', 'u', 'g', 'j', 'b', 'n'],
    'j': ['u', 'i', 'h', 'k', 'n', 'm'],
    'k': ['i', 'o', 'j', 'l', 'm'],
    'l': ['o', 'p', 'k'],
    'z': ['a', 's', 'x'],
    'x': ['z', 's', 'd', 'c'],
    'c': ['x', 'd', 'f', 'v'],
    'v': ['c', 'f', 'g', 'b'],
    'b': ['v', 'g', 'h', 'n'],
    'n': ['b', 'h', 'j', 'm'],
    'm': ['n', 'j', 'k'],
}

import bot.config as config

def generate_typo(text):
    """Introduce a single realistic typo into the text using QWERTY neighbors.

    Only mutates alphabetic characters that have known neighbors.
    Returns (typo_text, original_char, replacement_char, position) or
    (None, ...) if no suitable character was found.
    """
    # Collect all mutable positions (alphabetic chars with QWERTY neighbors)
    candidates = []
    for i, ch in enumerate(text):
        if ch.lower() in QWERTY_NEIGHBORS:
            candidates.append(i)

    if not candidates:
        return None, None, None, None

    # Pick a random position to mutate
    pos = random.choice(candidates)
    original_char = text[pos]
    neighbors = QWERTY_NEIGHBORS[original_char.lower()]
    replacement = random.choice(neighbors)

    # Preserve case
    if original_char.isupper():
        replacement = replacement.upper()

    typo_text = text[:pos] + replacement + text[pos + 1:]
    return typo_text, original_char, replacement, pos


async def send_with_typo_chance(channel, command, priority_label=""):
    """Send a command with a chance of sending a typo first.

    If the typo triggers:
      1. Sends the mistyped command
      2. Waits a short human-like "oh no" delay (0.3 - 1.2s)
      3. Sends the correct command

    Args:
        channel: The Discord channel to send to.
        command: The correct command string.
        priority_label: Optional label for HUD logging (e.g. "HPQ", "LPQ").

    Returns:
        True if a typo was sent, False if the command was sent cleanly.
    """
    if not channel:
        logger.error(f"Cannot send command '{command}' because channel is None.")
        HUD.system(f"⚠️ Erro: Canal do Discord indisponível. '{command}' não enviado.")
        return False

    if random.random() < config.typo_chance:
        typo_text, orig, repl, pos = generate_typo(command)

        if typo_text and typo_text != command:
            # Send the typo
            async with channel.typing():
                await asyncio.sleep(0.1 + random.random() * 0.3)
            await channel.send(typo_text)
                
            HUD.system(
                f"🫢 Typo! Enviado '{typo_text}' "
                f"('{orig}'→'{repl}' na pos {pos})"
            )
            logger.debug(
                f"Typo triggered: '{command}' → '{typo_text}' "
                f"[{priority_label}]"
            )

            # Brief "correction" delay — faster than normal human delay
            # because you notice a typo quickly
            correction_delay = 0.3 + random.random() * 0.9
            await asyncio.sleep(correction_delay)

            # Now send the correct command
            async with channel.typing():
                await asyncio.sleep(0.1 + random.random() * 0.3)
            await channel.send(command)
                
            HUD.system(f"Corrigido -> '{command}'")
            return True

    # No typo — send normally
    async with channel.typing():
        await asyncio.sleep(0.1 + random.random() * 0.3)
    await channel.send(command)
    return False
