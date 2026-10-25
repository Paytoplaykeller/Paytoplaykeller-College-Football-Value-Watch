"""Cross-game underdog mispricing hypothesis screen (research only).

Common pattern to TEST: large favorite's market-implied margin exceeds a
point-in-time opponent-network projection, while the underdog has independently
verified offensive survival and the favorite has margin-creation concerns.

Never turns three hindsight wins into a probability boost.
"""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite


@dataclass(frozen=True)
class MispricingEvidence:
    event_id: str
    as_of: datetime
    kickoff: datetime
    public_quote_at: datetime
    market_favorite_margin: float
    network_favorite_margin: float
    network_home_games_seen: int
    network_away_games_seen: int
    independent_model_agreement: bool | None
    favorite_drive_sustainability: bool | None
    favorite_margin_paths: int | None
    underdog_offensive_floor: bool | None
    underdog_cover_paths: int | None
    qb_ol_availability_verified: bool
    source: str


def screen(e: MispricingEvidence, *, discrepancy_threshold: float = 3.0) -> dict:
    if not e.source or any(t.tzinfo is None for t in
                           (e.as_of,e.kickoff,e.public_quote_at)):
        raise ValueError("Timestamped attributed research required")
    if not (e.public_quote_at <= e.as_of < e.kickoff):
        raise ValueError("Pregame quote must precede analysis and kickoff")
    if not all(isfinite(x) for x in
               (e.market_favorite_margin,e.network_favorite_margin)):
        raise ValueError("Invalid margin")
    if e.market_favorite_margin < 0 or discrepancy_threshold <= 0:
        raise ValueError("Favorite margin and threshold must be positive")
    gap=e.market_favorite_margin-e.network_favorite_margin
    if min(e.network_home_games_seen,e.network_away_games_seen)<3:
        return {"status":"INSUFFICIENT_SCHEDULE_SAMPLE","gap":gap,"bet_authorized":False}
    critical=(e.independent_model_agreement,e.favorite_drive_sustainability,
              e.favorite_margin_paths,e.underdog_offensive_floor,
              e.underdog_cover_paths)
    if any(x is None for x in critical) or not e.qb_ol_availability_verified:
        return {"status":"INCOMPLETE_PREGAME_EVIDENCE","gap":gap,"bet_authorized":False}
    favorite_fragile=(e.favorite_drive_sustainability is False or
                      e.favorite_margin_paths<2)
    dog_survives=(e.underdog_offensive_floor is True and
                  e.underdog_cover_paths>=2)
    if gap>=discrepancy_threshold and e.independent_model_agreement and favorite_fragile and dog_survives:
        status="PRIORITY_UNDERDOG_RESEARCH"
    elif gap>=discrepancy_threshold and dog_survives:
        status="WATCH_PRICE_DISLOCATION"
    else:
        status="NO_SIGNAL"
    return {"status":status,"gap":gap,"bet_authorized":False,
            "p_raw_delta":0.0,"stake_multiplier":1.0,
            "reason":"Hypothesis screen only; calibrated exact-line probability and EV still required"}
