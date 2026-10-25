"""Pregame FBS schedule-network ratings with learned conference effects.

Ridge regression on *past* game margins: team strength, conference residual,
and venue. Conference effects are regularized separately, not bolted on as
arbitrary SEC/Big Ten bonuses. Predictive performance must be validated.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
import numpy as np


@dataclass(frozen=True)
class NetworkGame:
    game_id: str
    kickoff: datetime
    season: int
    home_id: str
    away_id: str
    home_conference: str
    away_conference: str
    neutral: bool
    home_points: int | None
    away_points: int | None


@dataclass(frozen=True)
class NetworkRatings:
    as_of: datetime
    team_ratings: dict[str, float]
    conference_effects: dict[str, float]
    home_advantage: float
    team_game_counts: dict[str, int]
    training_games: int
    source: str

    def project(self, home: str, away: str, home_conference: str,
                away_conference: str, neutral: bool = False) -> dict:
        # Missing teams get a zero *prior*, not an invented observed rating.
        home_team = self.team_ratings.get(home, 0.0)
        away_team = self.team_ratings.get(away, 0.0)
        hc = self.conference_effects.get(home_conference, 0.0)
        ac = self.conference_effects.get(away_conference, 0.0)
        return {
            "projected_home_margin":home_team-away_team+hc-ac+
                (0.0 if neutral else self.home_advantage),
            "home_team_rating":home_team+hc,
            "away_team_rating":away_team+ac,
            "home_games_seen":self.team_game_counts.get(home,0),
            "away_games_seen":self.team_game_counts.get(away,0),
            "conference_effect_home":hc,
            "conference_effect_away":ac,
            "status":"RESEARCH_ONLY_NOT_BET",
        }


def fit_network(games: list[NetworkGame], as_of: datetime, *,
                lookback_seasons: int = 2, team_penalty: float = 15.0,
                conference_penalty: float = 90.0,
                max_margin: int = 35, min_games: int = 20) -> NetworkRatings:
    if as_of.tzinfo is None:
        raise ValueError("Timezone-aware as_of required")
    if team_penalty <= 0 or conference_penalty <= 0 or max_margin < 1:
        raise ValueError("Invalid regularization")
    current = as_of.year
    # Use game season, not calendar year, to handle January bowl games.
    eligible=[]
    ids=set()
    for g in games:
        if g.game_id in ids:
            raise ValueError("Duplicate game")
        ids.add(g.game_id)
        if g.kickoff.tzinfo is None:
            raise ValueError("Timezone-aware kickoff required")
        if (g.kickoff+timedelta(hours=6) >= as_of or
            g.home_points is None or g.away_points is None or
            g.season < current-lookback_seasons-1 or g.season>current):
            continue
        if not g.home_id or not g.away_id or not g.home_conference or not g.away_conference:
            continue
        eligible.append(g)
    if len(eligible)<min_games:
        raise ValueError("Insufficient completed pregame history")
    teams=sorted({v for g in eligible for v in (g.home_id,g.away_id)})
    confs=sorted({v for g in eligible for v in (g.home_conference,g.away_conference)})
    ti={k:i for i,k in enumerate(teams)}
    ci={k:i+len(teams) for i,k in enumerate(confs)}
    home_col=len(teams)+len(confs)
    x=np.zeros((len(eligible),home_col+1))
    y=np.zeros(len(eligible))
    weights=np.zeros(len(eligible))
    counts={t:0 for t in teams}
    for i,g in enumerate(eligible):
        x[i,ti[g.home_id]]+=1
        x[i,ti[g.away_id]]-=1
        x[i,ci[g.home_conference]]+=1
        x[i,ci[g.away_conference]]-=1
        x[i,home_col]=0 if g.neutral else 1
        y[i]=max(-max_margin,min(max_margin,g.home_points-g.away_points))
        age=(as_of-g.kickoff).total_seconds()/(365.25*86400)
        weights[i]=0.65**max(0,age)
        counts[g.home_id]+=1
        counts[g.away_id]+=1
    penalty=np.array([team_penalty]*len(teams)+
                     [conference_penalty]*len(confs)+[5.0])
    xtw=x.T*weights
    coef=np.linalg.solve(xtw@x+np.diag(penalty),xtw@y)
    return NetworkRatings(
        as_of=as_of,team_ratings={k:float(coef[i]) for k,i in ti.items()},
        conference_effects={k:float(coef[i]) for k,i in ci.items()},
        home_advantage=float(coef[home_col]),team_game_counts=counts,
        training_games=len(eligible),
        source="Pregame schedule-network ridge; capped scoring margins; "+
               "conference shrinkage; no market or injury inputs",
    )
