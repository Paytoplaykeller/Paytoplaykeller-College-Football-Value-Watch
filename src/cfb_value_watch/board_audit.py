"""Fail-closed FBS board completeness audit.

The scheduler/odds adapters must populate one row per scheduled FBS matchup.
This module DOES NOT fetch sportsbook or game data and cannot certify bets.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from datetime import datetime, timezone
from typing import Iterable, Mapping


@dataclass(frozen=True)
class CoverageIssue:
    game_id: str
    reason: str


@dataclass(frozen=True)
class BoardAudit:
    expected: int
    reviewed: int
    issues: tuple[CoverageIssue, ...]
    approved_bet_fingerprints: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.expected > 0 and self.expected == self.reviewed and not self.issues


def _fingerprint(review: Mapping) -> str:
    """Bind an approved BET to the exact evidence evaluated, not just its game ID."""
    payload = json.dumps(dict(review), sort_keys=True, default=str, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def audit_board(schedule: Iterable[Mapping], reviews: Iterable[Mapping],
                *, now: datetime | None = None,
                max_quote_age_minutes: int = 15) -> BoardAudit:
    """Require one review per scheduled game and auditable timing/evidence.

    Review statuses can be BET/WATCH/PASS, but BET is forbidden without explicit
    approval evidence. A stale/non-executable price must never be labeled BET.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone aware")
    expected = list(schedule)
    examined = list(reviews)
    issues: list[CoverageIssue] = []
    ids = [str(g.get("game_id", "")) for g in expected]
    if len(ids) != len(set(ids)) or any(not x for x in ids):
        issues.append(CoverageIssue("BOARD", "Duplicate or missing schedule game_id"))
    by_id: dict[str, Mapping] = {}
    for review in examined:
        ident = str(review.get("game_id", ""))
        if ident in by_id:
            issues.append(CoverageIssue(ident, "Duplicate matchup review"))
        by_id[ident] = review
    for g in expected:
        ident = str(g.get("game_id", ""))
        r = by_id.get(ident)
        if r is None:
            issues.append(CoverageIssue(ident, "UNREVIEWED scheduled matchup"))
            continue
        if not r.get("venue_verified"):
            issues.append(CoverageIssue(ident, "Venue/home field unverified"))
        if not r.get("injury_checked"):
            issues.append(CoverageIssue(ident, "Injury check missing"))
        if not r.get("offense_defense_checked"):
            issues.append(CoverageIssue(ident, "Offensive/defensive matchup check missing"))
        if not r.get("odds_checked"):
            issues.append(CoverageIssue(ident, "Odds comparison missing"))
        decision = r.get("decision")
        if decision not in {"BET", "WATCH", "PASS"}:
            issues.append(CoverageIssue(ident, "Missing/invalid BET-WATCH-PASS status"))
        if decision == "BET":
            required = (
                "price_executable", "two_way_market_verified", "independent_p_raw",
                "no_vig_prior_verified", "uncertainty_ev_verified",
                "mandatory_gates_passed", "quarter_kelly_checked",
                "max_price_checked", "bankroll_cap_checked",
            )
            for field in required:
                if r.get(field) is not True:
                    issues.append(CoverageIssue(ident, f"BET blocked: {field}"))
            ts = r.get("quote_time")
            if not isinstance(ts, datetime) or ts.tzinfo is None:
                issues.append(CoverageIssue(ident, "BET blocked: missing timezone-aware quote timestamp"))
            elif not 0 <= (now - ts).total_seconds() <= max_quote_age_minutes * 60:
                issues.append(CoverageIssue(ident, "BET blocked: stale/future quote"))
    for ident in set(by_id) - set(ids):
        issues.append(CoverageIssue(ident, "Review not in scheduled game board"))
    approved = tuple(sorted(_fingerprint(r) for r in examined if r.get("decision") == "BET")) if not issues and expected and len(expected) == len(by_id) else ()
    return BoardAudit(len(expected), len(by_id), tuple(issues), approved)


def verified_bets_only(audit: BoardAudit, reviews: Iterable[Mapping]) -> list[Mapping]:
    """Fail shut on incomplete board or any missing validation evidence."""
    if not audit.complete:
        return []
    requested = [r for r in reviews if r.get("decision") == "BET"]
    # Never reuse an earlier WATCH/PASS audit to authorize a different BET,
    # or accept a changed quote/gate result after that audit.
    if tuple(sorted(_fingerprint(r) for r in requested)) != audit.approved_bet_fingerprints:
        return []
    return requested
