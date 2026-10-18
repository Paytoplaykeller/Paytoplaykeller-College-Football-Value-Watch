"""Cross-conference diagnostic and postseason availability checks.

Conference performance is estimated from actual interconference matchups
AFTER opponent-adjusted network forecasts; no automatic conference bonus.
This is a diagnostic of residuals, not an independent strength rating to add
again to the network prediction.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from collections import defaultdict
from typing import Sequence


@dataclass(frozen=True)
class CrossConferenceForecast:
    game_id: str
    kickoff: datetime
    forecast_at: datetime
    home_conference: str
    away_conference: str
    predicted_home_margin: float
    actual_home_margin: float


def conference_residual_audit(
    games: Sequence[CrossConferenceForecast], *,
    min_games: int = 25,
) -> dict:
    """Measure out-of-sample conference residuals, no betting authorization."""
    ids=set()
    per_conference=defaultdict(list)
    pairs=defaultdict(list)
    n=0
    for g in games:
        if g.game_id in ids:
            raise ValueError("Duplicate game")
        ids.add(g.game_id)
        if (g.kickoff.tzinfo is None or g.forecast_at.tzinfo is None
            or g.forecast_at >= g.kickoff):
            raise ValueError("Historical forecast must precede kickoff")
        if not g.home_conference or not g.away_conference:
            raise ValueError("Missing conference")
        if g.home_conference == g.away_conference:
            continue
        residual=g.actual_home_margin-g.predicted_home_margin
        per_conference[g.home_conference].append(residual)
        per_conference[g.away_conference].append(-residual)
        key=tuple(sorted((g.home_conference,g.away_conference)))
        # Residual from lexicographically first conference's perspective.
        pairs[key].append(residual if g.home_conference==key[0] else -residual)
        n+=1
    def summarize(vals):
        count=len(vals)
        if count<min_games:
            return {"n":count,"status":"INSUFFICIENT_SAMPLE",
                    "mean_margin_residual":None,"uncertainty_95":None}
        mu=sum(vals)/count
        sd=sqrt(sum((x-mu)**2 for x in vals)/(count-1)) if count>1 else 0.0
        return {"n":count,"status":"RESEARCH_ONLY",
                "mean_margin_residual":mu,
                "uncertainty_95":1.96*sd/sqrt(count)}
    return {"status":"RESEARCH_ONLY_NOT_BET",
            "cross_conference_games":n,
            "conference_residuals":{k:summarize(v) for k,v in sorted(per_conference.items())},
            "conference_pairs":{" vs ".join(k):summarize(v) for k,v in sorted(pairs.items())},
            "no_additive_bonus":True,
            "limitations":["Residuals are not causal conference strength",
                           "Nonrandom schedules and selection effects",
                           "Do not double-count conference effect already in network model"]}


@dataclass(frozen=True)
class PostseasonAvailability:
    event_id: str
    as_of: datetime
    kickoff: datetime
    qb_status_verified: bool
    offensive_line_verified: bool
    opt_outs_and_transfers_verified: bool
    coaching_staff_verified: bool
    defensive_units_verified: bool
    special_teams_verified: bool
    roster_source: str


def postseason_gate(e: PostseasonAvailability) -> dict:
    if not e.roster_source or e.as_of.tzinfo is None or e.kickoff.tzinfo is None:
        raise ValueError("Attributable timezone-aware postseason report required")
    if e.as_of>=e.kickoff:
        raise ValueError("Post-kickoff information not allowed")
    checks={
        "quarterback":e.qb_status_verified,
        "offensive line":e.offensive_line_verified,
        "opt-outs and transfers":e.opt_outs_and_transfers_verified,
        "coaching changes":e.coaching_staff_verified,
        "defensive units":e.defensive_units_verified,
        "special teams":e.special_teams_verified,
    }
    missing=[name for name,ok in checks.items() if not ok]
    return {"status":"WATCH_INCOMPLETE_AVAILABILITY" if missing else "ROSTER_CHECKS_COMPLETE",
            "missing":missing,"bet_authorized":False,
            "reason":"Postseason availability alone cannot establish calibrated EV"}
