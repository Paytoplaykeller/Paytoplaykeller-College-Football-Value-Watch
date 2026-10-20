from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from numbers import Real


def validate_american_odds(odds: int) -> int:
    """Reject malformed betting prices; US prices are <= -100 or >= +100."""
    if type(odds) is not int or -100 < odds < 100:
        raise ValueError("American odds must be an integer <= -100 or >= +100")
    return odds


def _validate_probability(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{label} must be finite and in [0,1]")


def american_to_break_even(odds: int) -> float:
    validate_american_odds(odds)
    return 100 / (odds + 100) if odds > 0 else (-odds) / ((-odds) + 100)


def no_vig_two_way(odds_a: int, odds_b: int) -> tuple[float, float]:
    pa = american_to_break_even(odds_a)
    pb = american_to_break_even(odds_b)
    total = pa + pb
    return pa / total, pb / total


def adjusted_probability(q_market: float, p_raw: float, lam: float) -> float:
    _validate_probability(q_market, "q_market")
    _validate_probability(p_raw, "p_raw")
    _validate_probability(lam, "lambda")
    return q_market + lam * (p_raw - q_market)


def decimal_odds(american: int) -> float:
    validate_american_odds(american)
    return 1 + (american / 100 if american > 0 else 100 / (-american))


def expected_value_per_unit(p: float, american: int) -> float:
    _validate_probability(p, "p")
    d = decimal_odds(american)
    return p * (d - 1) - (1 - p)


def full_kelly_fraction(p: float, american: int) -> float:
    _validate_probability(p, "p")
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
