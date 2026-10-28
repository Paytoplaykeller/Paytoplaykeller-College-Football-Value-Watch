"""2026-only qualitative LEAN path; never converts public odds into a certified BET.

The research path ranks available evidence without requiring an executable quote,
bankroll, or an independent probability. Certified BET remains governed by the
existing strict model. No orders, stakes, or private ledger writes occur here.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class SeasonSignal:
    name: str
    favors_selection: bool
    source: str
    observed_at: datetime
    season: int = 2026


@dataclass(frozen=True)
class LeanCandidate:
    selection: str
    event_id: str
    kickoff: datetime
    evaluated_at: datetime
    signals: tuple[SeasonSignal, ...]
    critical_contradiction: bool = False
    already_placed: bool = False


@dataclass(frozen=True)
class LeanResult:
    selection: str
    status: Literal["LEAN", "REVIEW", "PASS"]
    supportive: int
    opposing: int
    reasons: tuple[str, ...]
    certified_bet: bool = False


def assess_lean(candidate: LeanCandidate) -> LeanResult:
    """Fail closed on chronology, but permit research with partial noncritical info."""
    reasons = []
    if not candidate.selection or not candidate.event_id:
        return LeanResult(candidate.selection, "PASS", 0, 0, ("Selection/event missing",))
    if (candidate.kickoff.tzinfo is None or candidate.evaluated_at.tzinfo is None
            or candidate.evaluated_at >= candidate.kickoff):
        return LeanResult(candidate.selection, "PASS", 0, 0, ("Invalid pregame timestamps",))
    if not candidate.signals:
        return LeanResult(candidate.selection, "REVIEW", 0, 0, ("No attributable 2026 signals",))
    for s in candidate.signals:
        if (s.season != 2026 or not s.source or not s.name
                or s.observed_at.tzinfo is None
                or s.observed_at > candidate.evaluated_at):
            return LeanResult(candidate.selection, "PASS", 0, 0,
                              ("Unattributed, non-2026 or future-dated evidence",))
    supportive = sum(s.favors_selection for s in candidate.signals)
    opposing = len(candidate.signals) - supportive
    if candidate.critical_contradiction:
        return LeanResult(candidate.selection, "REVIEW", supportive, opposing,
                          ("Critical personnel or thesis contradiction unresolved",))
    if supportive >= 2 and supportive > opposing:
        reasons.append("Multiple attributed 2026 supporting signals")
        if candidate.already_placed:
            reasons.append("Existing position: no automatic additional exposure")
        return LeanResult(candidate.selection, "LEAN", supportive, opposing, tuple(reasons))
    return LeanResult(candidate.selection, "REVIEW", supportive, opposing,
                      ("Insufficient net qualitative support",))


def rank_leans(candidates: tuple[LeanCandidate, ...], limit: int = 5) -> list[LeanResult]:
    if limit < 1:
        raise ValueError("limit must be positive")
    results = [assess_lean(c) for c in candidates]
    priority = {"LEAN": 0, "REVIEW": 1, "PASS": 2}
    return sorted(results, key=lambda x: (priority[x.status],
                                           -(x.supportive-x.opposing), x.selection))[:limit]
