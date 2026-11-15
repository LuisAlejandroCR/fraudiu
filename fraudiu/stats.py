# stats.py: Wilson score intervals and the degenerate-output check used as a cheap
# fluency guard on steered generations. Pure Python, no dependencies.
from __future__ import annotations

import math
import re


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """(rate, low, high) for k successes in n trials; (nan, nan, nan) when n == 0."""
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


_REPEAT = re.compile(r"(\b\w+\b)(?:\W+\1\b){5,}", re.IGNORECASE)


def is_degenerate(text: str) -> bool:
    """Empty, a word repeated 6+ times in a row, or under 25% distinct characters in 40+."""
    t = (text or "").strip()
    if not t:
        return True
    if _REPEAT.search(t):
        return True
    return len(t) >= 40 and len(set(t)) / len(t) < 0.25 and len(set(t)) < 12


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for paired binary outcomes. b and c are the discordant
    counts (event only in condition A, event only in condition B): a binomial test of b against
    Binomial(b + c, 0.5). 1.0 when there are no discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)
