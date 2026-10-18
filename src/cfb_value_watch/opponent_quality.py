"""Point-in-time opponent-quality evidence for CFB forecasts.

Avoid raw records, ranking bonuses and hindsight. Build strength of schedule
and strength of victories from ratings frozen before each game.
"""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite

@dataclass(frozen=True)
class OpponentResult:
    team: str
    opponent: str
    kickoff: datetime
    snapshot_at: datetime
    opponent_rating: float
    rating_source: str
    points_for: int
    points_against: int
    neutral: bool = False
    away: bool = False


def quality_profile(team: str, games: list[OpponentResult], as_of: datetime,
                    *, min_games: int = 3) -> dict:
    if as_of.tzinfo is None:
        raise ValueError("Timestamp-aware evaluation required")
    rows=[]
    for g in games:
        if g.team != team:
            continue
        if (not g.rating_source or g.kickoff.tzinfo is None
            or g.snapshot_at.tzinfo is None or
            not (g.snapshot_at < g.kickoff < as_of)):
            raise ValueError("Opponent rating must be attributable and pregame")
        if not isfinite(g.opponent_rating):
            raise ValueError("Invalid opponent rating")
        if g.points_for < 0 or g.points_against < 0:
            raise ValueError("Invalid score")
        rows.append(g)
    if len(rows) < min_games:
        return {"status":"INSUFFICIENT_EVIDENCE","team":team,"games":len(rows)}
    wins=[g for g in rows if g.points_for>g.points_against]
    losses=[g for g in rows if g.points_for<g.points_against]
    return {
        "status":"RESEARCH_ONLY",
        "team":team,
        "games":len(rows),
        "wins":len(wins),
        "losses":len(losses),
        "schedule_strength":sum(g.opponent_rating for g in rows)/len(rows),
        "quality_of_wins":sum(g.opponent_rating for g in wins)/len(wins) if wins else None,
        "quality_of_losses":sum(g.opponent_rating for g in losses)/len(losses) if losses else None,
        "opponent_adjusted_margin":sum(
            (g.points_for-g.points_against)+g.opponent_rating for g in rows)/len(rows),
        "ranked_wins_not_used":True,
        "model_bet_authorized":False,
    }
