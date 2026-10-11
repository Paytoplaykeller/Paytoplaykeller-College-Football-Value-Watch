from __future__ import annotations
from dataclasses import dataclass


def american_to_break_even(odds: int) -> float:
    if odds == 0:
        raise ValueError("American odds cannot be zero")
    return odds / (odds + 100) if odds > 0 else (-odds) / ((-odds) + 100)


def no_vig_two_way(odds_a: int, odds_b: int) -> tuple[float, float]:
    pa = american_to_break_even(odds_a)
    pb = american_to_break_even(odds_b)
    total = pa + pb
    return pa / total, pb / total


def adjusted_probability(q_market: float, p_raw: float, lam: float) -> float:
    if not (0 <= q_market <= 1 and 0 <= p_raw <= 1 and 0 <= lam <= 1):
        raise ValueError("Probabilities and lambda must be in [0,1]")
    return q_market + lam * (p_raw - q_market)


def decimal_odds(american: int) -> float:
    return 1 + (american / 100 if american > 0 else 100 / (-american))


def expected_value_per_unit(p: float, american: int) -> float:
    d = decimal_odds(american)
    return p * (d - 1) - (1 - p)


def full_kelly_fraction(p: float, american: int) -> float:
    d = decimal_odds(american)
    b = d - 1
    q = 1 - p
    return max(0.0, (b * p - q) / b)


def quarter_kelly_fraction(p: float, american: int) -> float:
    return 0.25 * full_kelly_fraction(p, american)


@dataclass(frozen=True)
class BetEvaluation:
    selection: str
    odds: int
    q_market: float
    p_raw: float
    lam: float

    @property
    def break_even(self) -> float:
        return american_to_break_even(self.odds)

    @property
    def p_adj(self) -> float:
        return adjusted_probability(self.q_market, self.p_raw, self.lam)

    @property
    def ev(self) -> float:
        return expected_value_per_unit(self.p_adj, self.odds)

    @property
    def quarter_kelly(self) -> float:
        return quarter_kelly_fraction(self.p_adj, self.odds)
