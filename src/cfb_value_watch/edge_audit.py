"""Auditable point-in-time betting edge evaluation.

Never constructs model probabilities from outcomes or closing lines.
A historical backtest is NOT a live betting authorization.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from statistics import mean

@dataclass(frozen=True)
class HistoricalDecision:
    game_id: str
    kickoff: datetime
    forecast_at: datetime
    odds_at: datetime
    selection: str
    market: str
    line: float | None
    offered_american: int
    no_vig_market_prior: float
    adjusted_win_probability: float
    adjusted_push_probability: float
    # Actual outcome is evaluated ONLY after the original forecast is frozen.
    outcome: str
    model_version: str
    forecast_source: str
    price_source: str
    # Closing price is diagnostic, not a forecast input.
    closing_american: int | None = None


def decimal_profit(odds: int) -> float:
    if type(odds) is not int or abs(odds) < 100:
        raise ValueError("Invalid American odds")
    return odds/100 if odds > 0 else 100/(-odds)


def evaluate_ticket(d: HistoricalDecision) -> dict:
    if not d.game_id or not d.model_version or not d.forecast_source or not d.price_source:
        raise ValueError("Missing provenance")
    if d.kickoff.tzinfo is None or d.forecast_at.tzinfo is None or d.odds_at.tzinfo is None:
        raise ValueError("Timezone-aware timestamps required")
    if not (d.forecast_at < d.kickoff and d.odds_at < d.kickoff):
        raise ValueError("Forecast and quote must precede kickoff")
    if not all(isfinite(x) for x in (d.no_vig_market_prior,
                                    d.adjusted_win_probability,d.adjusted_push_probability)):
        raise ValueError("Invalid probabilities")
    p=d.adjusted_win_probability
    push=d.adjusted_push_probability
    if not (0 <= p <= 1 and 0 <= push <= 1 and p+push <= 1+1e-12
            and 0 <= d.no_vig_market_prior <= 1):
        raise ValueError("Invalid probability range")
    if d.outcome not in ("WIN","LOSS","PUSH"):
        raise ValueError("Outcome must be WIN, LOSS or PUSH")
    b=decimal_profit(d.offered_american)
    loss=max(0.0,1-p-push)
    ev=p*b-loss
    full_kelly=max(0.0,(b*p-loss)/(b*(p+loss))) if p+loss>0 else 0.0
    realized={"WIN":b,"LOSS":-1.0,"PUSH":0.0}[d.outcome]
    return {
        "game_id":d.game_id,"selection":d.selection,"expected_value":ev,
        "quarter_kelly_ceiling":0.25*full_kelly,
        "realized_unit_return":realized,
        "market_prior":d.no_vig_market_prior,
        "model_probability":p,
        "model_version":d.model_version,
    }


def audit_decisions(records: list[HistoricalDecision], *,
                    min_games: int = 200, min_seasons: int = 2) -> dict:
    if not records:
        raise ValueError("No independently recorded decisions")
    ids=set()
    years=set()
    rows=[]
    for d in records:
        # One bet per game in the *independent sample*. Repeated tickets are
        # exposures, not additional evidence of forecasting skill.
        if d.game_id in ids:
            raise ValueError("Duplicate game would inflate sample size")
        ids.add(d.game_id)
        years.add(d.kickoff.year)
        rows.append(evaluate_ticket(d))
    if len(rows)<min_games or len(years)<min_seasons:
        return {"status":"INSUFFICIENT_EVIDENCE","games":len(rows),
                "seasons":len(years),"approved_for_live_betting":False}
    realized=[r["realized_unit_return"] for r in rows]
    wins=[1.0 if d.outcome=="WIN" else 0.0 for d in records]
    model_brier=mean((d.adjusted_win_probability-w)**2 for d,w in zip(records,wins))
    market_brier=mean((d.no_vig_market_prior-w)**2 for d,w in zip(records,wins))
    # When pushes exist, these binary scores are only approximate; a proper
    # three-outcome scoring rule must be used for a production audit.
    if any(d.adjusted_push_probability>0 for d in records):
        return {"status":"REQUIRES_THREE_WAY_SCORING","games":len(rows),
                "approved_for_live_betting":False}
    equity=0.0
    peak=0.0
    max_drawdown=0.0
    for value in realized:
        equity+=value
        peak=max(peak,equity)
        max_drawdown=max(max_drawdown,peak-equity)
    return {"status":"RESEARCH_ONLY","games":len(rows),"seasons":len(years),
            "flat_stake_roi":mean(realized),
            "model_brier":model_brier,"market_brier":market_brier,
            "brier_improvement":market_brier-model_brier,
            "max_drawdown_units":max_drawdown,
            "approved_for_live_betting":False,
            "caveat":"No causal edge proven; verify frozen pregame provenance and multiple-hypothesis controls"}
