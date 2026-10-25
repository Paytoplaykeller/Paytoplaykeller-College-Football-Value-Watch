"""Fail-closed certification for advisory-only college football recommendations.

This module validates supplied evidence. It does not generate forecasts, fetch
sportsbook offers, validate that an external source is genuine, or place wagers.
Production integrations must separately authenticate every evidence field.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from typing import Mapping

from .model import adjusted_probability, expected_value_per_unit, quarter_kelly_fraction


@dataclass(frozen=True)
class CertificationEvidence:
    selection: str
    market: str
    odds: int
    line: float
    event_id: str
    source_revision: str
    model_run_id: str
    quote_timestamp: datetime
    evaluated_at: datetime
    executable_quote_verified: bool = False
    sportsbook: str = ""
    q_market: float | None = None
    p_raw: float | None = None
    lam: float | None = None
    model_dispersion_points: float | None = None
    independent_forecast_verified: bool = False
    no_vig_same_market_verified: bool = False
    availability_verified: bool = False
    replacements_verified: bool = False
    thesis_verified: bool = False
    opponent_strength_verified: bool = False
    venue_weather_verified: bool = False
    gate_results: Mapping[str, bool] = field(default_factory=dict)
    available_bankroll: float | None = None
    total_correlated_exposure: float | None = None
    proposed_stake: float | None = None
    large_wager: bool = False
    max_quote_age_seconds: int = 120


@dataclass(frozen=True)
class CertificationResult:
    status: str
    blockers: tuple[str, ...]
    p_adj: float | None = None
    ev: float | None = None
    quarter_kelly_cap: float | None = None


REQUIRED_GATES = (
    "defense_availability", "favorite_margin", "large_underdog",
    "offensive_survival", "correlated_injury", "thesis_consistency",
)


def certify_bet(e: CertificationEvidence) -> CertificationResult:
    blockers = []
    def require(ok: bool, message: str) -> None:
        if not ok:
            blockers.append(message)

    require(all((e.selection, e.market, e.event_id, e.source_revision, e.model_run_id)),
            "Missing attributable event/model evidence")
    require(e.executable_quote_verified is True and bool(e.sportsbook),
            "No authenticated executable sportsbook quotation")
    require(e.independent_forecast_verified is True, "No independently validated own-model forecast")
    require(e.no_vig_same_market_verified is True, "No paired same-market no-vig prior")
    require(e.availability_verified is True and e.replacements_verified is True,
            "Injury, quarterback, specialist or replacement verification incomplete")
    require(e.thesis_verified is True and e.opponent_strength_verified is True and e.venue_weather_verified is True,
            "Matchup, opponent/conference strength, weather or thesis evidence incomplete")
    for name in REQUIRED_GATES:
        require(e.gate_results.get(name) is True, f"Gate not verified/passed: {name}")
    valid_times = (isinstance(e.quote_timestamp, datetime) and isinstance(e.evaluated_at, datetime)\n                   and e.quote_timestamp.tzinfo is not None and e.evaluated_at.tzinfo is not None\n                   and e.quote_timestamp.utcoffset() is not None and e.evaluated_at.utcoffset() is not None)\n    require(valid_times,
            "Timezone-aware timestamps required")
    require(type(e.max_quote_age_seconds) is int and 0 < e.max_quote_age_seconds <= 120,\n            "Invalid quote-freshness limit")\n    if valid_times and type(e.max_quote_age_seconds) is int:
        age = (e.evaluated_at.astimezone(timezone.utc) -
               e.quote_timestamp.astimezone(timezone.utc)).total_seconds()
        require(0 <= age <= e.max_quote_age_seconds, "Stale or future-dated quote")
    require(type(e.model_dispersion_points) in (int, float) and
            isfinite(e.model_dispersion_points) and 0 <= e.model_dispersion_points <= 4.5,
            "Missing or excessive model dispersion")
    valid_probs = all(type(x) in (int, float) and
                      isfinite(x) and 0 <= x <= 1
                      for x in (e.q_market, e.p_raw, e.lam))
    require(valid_probs, "Missing or invalid calibrated probabilities")
    valid_money = all(type(x) in (int, float) and
                      isfinite(x) and x >= 0
                      for x in (e.available_bankroll, e.total_correlated_exposure,
                                e.proposed_stake))
    require(valid_money and e.available_bankroll > 0, "Verified bankroll/exposure/stake missing")
    if blockers:
        return CertificationResult("NO_BET", tuple(blockers))
    try:
        p_adj = adjusted_probability(e.q_market, e.p_raw, e.lam)
        ev = expected_value_per_unit(p_adj, e.odds)
        cap = quarter_kelly_fraction(p_adj, e.odds) * e.available_bankroll
    except (ValueError, ZeroDivisionError):
        return CertificationResult("NO_BET", ("Invalid odds or probability calculation",))
    min_ev = 0.07 if e.large_wager else 0.04
    require(ev >= min_ev, "Adjusted EV below configured threshold")
    require(e.proposed_stake > 0 and e.proposed_stake <= cap,
            "Stake exceeds quarter-Kelly limit or is zero")
    require(e.total_correlated_exposure + e.proposed_stake <= e.available_bankroll,
            "Insufficient verified uncommitted bankroll")
    return CertificationResult("NO_BET" if blockers else "BET",
                               tuple(blockers), p_adj, ev, cap)
