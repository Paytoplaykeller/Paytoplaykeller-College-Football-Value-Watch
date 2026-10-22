"""Totals-specific evidence and exact integer-score settlement probabilities.

A spread forecast never substitutes for a calibrated total-points distribution.
Missing pregame inputs or contradiction => no totals BET.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class TotalsEvidence:
    # All fields must be verified as of a timestamp before kickoff.
    total_line: float
    side: str
    calibrated_total_distribution: Mapping[int, float] | None
    distribution_source: str | None
    possessions_verified: bool
    both_offenses_sustainable: bool
    qb_ol_availability_verified: bool
    defensive_matchup_consistent: bool
    weather_verified: bool
    tempo_and_efficiency_verified: bool
    explosive_dependency_low: bool
    thesis_consistent: bool


def total_win_push_loss(dist: Mapping[int, float], line: float, side: str):
    if side not in ("Over", "Under") or not isfinite(line) or not dist:
        raise ValueError("Invalid totals contract or distribution")
    if any(type(k) is not int or type(v) not in (int, float)
           or not isfinite(v) or v < 0 for k,v in dist.items()):
        raise ValueError("Invalid total-score probability")
    if abs(sum(dist.values())-1) > 1e-6:
        raise ValueError("Total probabilities must sum to one")
    if side=="Over":
        win=sum(p for points,p in dist.items() if points>line)
    else:
        win=sum(p for points,p in dist.items() if points<line)
    push=sum(p for points,p in dist.items() if points==line)
    return win,push,max(0.0,1-win-push)


def totals_blockers(e: TotalsEvidence | None, p_raw: float | None):
    if e is None:
        return ["Totals Viability Gate: evidence missing"]
    failures=[]
    if not e.distribution_source or e.calibrated_total_distribution is None:
        failures.append("calibrated total-points distribution missing")
    checks={
        "possessions":e.possessions_verified,
        "both offenses sustainable":e.both_offenses_sustainable,
        "QB/OL availability":e.qb_ol_availability_verified,
        "defensive matchup":e.defensive_matchup_consistent,
        "weather":e.weather_verified,
        "tempo and scoring efficiency":e.tempo_and_efficiency_verified,
        "explosive-play dependence":e.explosive_dependency_low,
        "thesis consistency":e.thesis_consistent,
    }
    failures.extend(name+" unverified or contradictory" for name,ok in checks.items() if not ok)
    if e.calibrated_total_distribution is not None:
        try:
            win,push,_=total_win_push_loss(e.calibrated_total_distribution,e.total_line,e.side)
            if push>1e-9:
                failures.append("push probability requires three-way EV")
            if p_raw is not None and abs(win-p_raw)>1e-6:
                failures.append("p_raw differs from exact total-cover probability")
        except ValueError as exc:
            failures.append(str(exc))
    return ["Totals Viability Gate: "+x for x in failures]
