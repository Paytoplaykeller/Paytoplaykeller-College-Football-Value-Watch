from __future__ import annotations
from dataclasses import dataclass
from .model import american_to_break_even, expected_value_per_unit, quarter_kelly_fraction

@dataclass(frozen=True)
class FuturesEvaluation:
    market: str
    selection: str
    odds: int
    p_adj: float
    capital_lockup_haircut: float = 1.0

    @property
    def break_even(self) -> float:
        return american_to_break_even(self.odds)

    @property
    def raw_ev(self) -> float:
        return expected_value_per_unit(self.p_adj, self.odds)

    @property
    def adjusted_ev(self) -> float:
        return self.raw_ev * self.capital_lockup_haircut

    @property
    def quarter_kelly(self) -> float:
        return quarter_kelly_fraction(self.p_adj, self.odds) * self.capital_lockup_haircut
