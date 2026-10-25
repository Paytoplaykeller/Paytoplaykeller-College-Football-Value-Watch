"""Underdog-day trend audit: never learn from a handful of completed games.

Use only pre-kickoff quotes and archived model forecasts. The day-of outcomes
are recorded for diagnostics but NEVER boost an unplayed game's probability.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import sqrt, isfinite


@dataclass(frozen=True)
class UnderdogSample:
    game_id: str
    kickoff: datetime
    snapshot_at: datetime
    spread: float
    cover: bool
    no_vig_cover_probability: float
    source: str
    home: bool


@dataclass(frozen=True)
class TrendAudit:
    status: str
    n: int
    observed_cover_rate: float | None
    expected_cover_rate: float | None
    residual_edge: float | None
    conservative_lower_bound: float | None
    adjustment_allowed: bool = False


def audit_underdog_trend(
    records: list[UnderdogSample],
    *,
    evaluation_before: datetime,
    min_games: int = 200,
    min_seasons: int = 2,
    min_excess_cover: float = 0.04,
) -> TrendAudit:
    """Exploratory residual analysis, not authorization to change probabilities.

    Only independent, completed games *before* evaluation timestamp are used.
    One record per game. Two-sided no-vig pregame probabilities are mandatory.
    """
    if evaluation_before.tzinfo is None:
        raise ValueError("Evaluation timestamp must be timezone aware")
    ids=set()
    valid=[]
    for r in records:
        if r.game_id in ids:
            raise ValueError("Duplicate game in underdog trend")
        ids.add(r.game_id)
        if not r.source or r.kickoff.tzinfo is None or r.snapshot_at.tzinfo is None:
            raise ValueError("Missing source or timestamp")
        if not (r.snapshot_at < r.kickoff < evaluation_before):
            raise ValueError("Non-pregame quote or future game in sample")
        if r.spread <= 0 or not isfinite(r.spread):
            raise ValueError("Sample must contain genuine underdogs")
        if not isfinite(r.no_vig_cover_probability) or not 0 <= r.no_vig_cover_probability <= 1:
            raise ValueError("Missing/invalid no-vig probability")
        valid.append(r)
    n=len(valid)
    if not n:
        return TrendAudit("NO_EVIDENCE",0,None,None,None,None)
    observed=sum(r.cover for r in valid)/n
    expected=sum(r.no_vig_cover_probability for r in valid)/n
    residual=observed-expected
    # Conservative variance estimate for Bernoulli residuals, not a claim
    # of independence across correlated games or multiple hypotheses.
    se=sqrt(sum(r.no_vig_cover_probability*(1-r.no_vig_cover_probability)
                for r in valid))/n
    lower=residual-1.96*se
    seasons=len({r.kickoff.year for r in valid})
    status=("INSUFFICIENT_EVIDENCE" if n<min_games or seasons<min_seasons
            else "NO_REPLICATED_EDGE" if lower<=min_excess_cover
            else "HYPOTHESIS_REQUIRES_INDEPENDENT_HOLDOUT")
    return TrendAudit(status,n,observed,expected,residual,lower,False)


def same_day_dog_signal(completed_games: int, covers: int) -> dict:
    """Never infer a profitable late-game underdog trend from early outcomes."""
    if completed_games < 0 or not 0 <= covers <= completed_games:
        raise ValueError("Invalid scoreboard sample")
    return {"completed":completed_games,"covers":covers,
            "status":"DESCRIPTIVE_ONLY","p_raw_delta":0.0,
            "lambda_multiplier":1.0,"stake_multiplier":1.0,
            "reason":"Same-day underdog results do not establish a predictive edge"}
