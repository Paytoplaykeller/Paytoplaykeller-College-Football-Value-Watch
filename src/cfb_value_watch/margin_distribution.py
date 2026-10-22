"""Exact spread-cover probability from a calibrated, timestamped margin distribution.

Margin = points scored by the selected team minus opponent points.
Positive spread s covers if margin + s > 0. Integer spreads can push.
No probability distribution is inferred from a single projected margin.
"""
from __future__ import annotations
from math import isfinite
from typing import Mapping


def cover_push_loss(margins: Mapping[int, float], spread: float) -> tuple[float, float, float]:
    if not margins or not isfinite(spread):
        raise ValueError("Missing or invalid margin distribution")
    if any(not isinstance(m, int) or isinstance(m, bool) or
           not isfinite(p) or p < 0 for m, p in margins.items()):
        raise ValueError("Invalid margin or probability")
    if abs(sum(margins.values()) - 1.0) > 1e-6:
        raise ValueError("Margin probabilities must sum to one")
    win = sum(p for margin, p in margins.items() if margin + spread > 1e-9)
    push = sum(p for margin, p in margins.items() if abs(margin + spread) <= 1e-9)
    return win, push, max(0.0, 1.0 - win - push)
