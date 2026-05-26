"""
Oracle v2 - Modern Ornamental Separators
Simple helpers — no more complex "frame builders" that break at different widths.
"""


def separator_heavy(width: int) -> str:
    """═══════▪═══════ style"""
    half = max(1, (width - 1) // 2)
    return ("═" * half + "▪" + "═" * half)[:width]


def separator_medium(width: int) -> str:
    """───── ▪ ───── style"""
    half = max(1, (width - 3) // 2)
    return ("─" * half + " ▪ " + "─" * half)[:width]


def separator_light(width: int) -> str:
    """· · · · · · · style"""
    return ("· " * (width // 2))[:width]
