"""Pregame favorite-margin fragility, independent of final results.

This diagnostic flags situations like Kentucky/Oklahoma for review. It never
adds an arbitrary probability boost, infers future turnovers, or authorizes BET.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FavoriteFragilityEvidence:
    favorite: str
    underdog: str
    snapshot_at: datetime
    kickoff: datetime
    sources: tuple[str, ...]
    favorite_spread: float
    favorite_offensive_drive_sustainability: bool | None
    favorite_ol_viable: bool | None
    favorite_scoring_independent_of_defense_st: bool | None
    favorite_two_separation_paths: bool | None
    dog_offensive_floor: bool | None
    dog_qb_ol_viable: bool | None
    dog_multiple_cover_paths: bool | None


def favorite_fragility_gate(e: FavoriteFragilityEvidence) -> dict:
    if not e.sources or e.snapshot_at.tzinfo is None or e.kickoff.tzinfo is None:
        raise ValueError("Attributable timezone-aware pregame evidence required")
    if e.snapshot_at >= e.kickoff:
        raise ValueError("Post-kickoff information prohibited")
    if e.favorite_spread > -6:
        return {"status":"NOT_APPLICABLE","flag":False,"p_raw_delta":0.0,
                "lambda_multiplier":1.0}
    required={
        "favorite offensive drive sustainability":e.favorite_offensive_drive_sustainability,
        "favorite OL viability":e.favorite_ol_viable,
        "favorite scoring independent of defensive/ST TDs":e.favorite_scoring_independent_of_defense_st,
        "favorite independent separation paths":e.favorite_two_separation_paths,
        "underdog sustainable scoring floor":e.dog_offensive_floor,
        "underdog QB/OL viability":e.dog_qb_ol_viable,
        "underdog multiple cover paths":e.dog_multiple_cover_paths,
    }
    unknown=[name for name,value in required.items() if value is None]
    if unknown:
        return {"status":"INCOMPLETE_RESEARCH","flag":False,
                "missing":unknown,"p_raw_delta":0.0,"lambda_multiplier":1.0}
    favorite_contradictions=[
        name for name in list(required)[:4] if required[name] is False
    ]
    dog_paths=all(required[name] is True for name in list(required)[4:])
    flag=bool(favorite_contradictions and dog_paths)
    return {
        "status":"FAVORITE_MARGIN_FRAGILITY_WATCH" if flag else "NO_FLAG",
        "flag":flag,
        "favorite_contradictions":favorite_contradictions,
        "dog_paths_verified":dog_paths,
        "p_raw_delta":0.0,
        "lambda_multiplier":1.0,
        "reason":"Investigate underdog spread and favorite margin distribution; no automatic bet"
    }
