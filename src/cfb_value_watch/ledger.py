from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal

Status = Literal["CONFIRMED_PLACED_OPEN", "SETTLED_WIN", "SETTLED_LOSS", "PUSH", "CASHED_OUT"]

@dataclass
class Wager:
    date: str
    game: str
    market: str
    selection: str
    line: str
    odds: int | None
    stake: float
    potential_payout: float | None = None
    sportsbook: str | None = None
    status: Status = "CONFIRMED_PLACED_OPEN"
    closing_line: str | None = None
    closing_price: int | None = None
    result: str | None = None
    profit_loss: float | None = None
    clv_note: str | None = None
    p_raw: float | None = None
    p_adj: float | None = None
    ev: float | None = None
    calibration_tag: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
