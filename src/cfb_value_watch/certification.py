"""Strict BET certification boundary. Public odds are research, never execution evidence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math

from .model import adjusted_probability, expected_value_per_unit, quarter_kelly_fraction, no_vig_two_way


@dataclass(frozen=True)
class CertificationInput:
    selection: str
    offered_american_odds: int | None
    opposite_american_odds: int | None
    public_quote_at: datetime | None
    executable_hard_rock_verified: bool
    executable_quote_at: datetime | None
    sportsbook_authorized_in_location: bool
    forecast_source: str | None
    calibrated_independent_forecast: bool
    p_raw: float | None
    lambda_justification: str | None
    lam: float | None
    model_dispersion_points: float | None
    availability_verified: bool
    all_protective_gates_passed: bool
    verified_bankroll: float | None
    proposed_stake: float | None


@dataclass(frozen=True)
class CertificationResult:
    decision: str
    blockers: tuple[str, ...]
    p_adj: float | None = None
    ev: float | None = None
    max_quarter_kelly_stake: float | None = None


def certify_bet(
    item: CertificationInput,
    *,
    now: datetime | None = None,
    max_quote_age_seconds: int = 900,
    minimum_ev: float = 0.04,
    max_dispersion_points: float = 4.5,
) -> CertificationResult:
    """Only issue BET when *all* independent evidence and gates pass.

    Missing/invalid inputs always produce NO BET; this function cannot place a wager.
    Both sides must be quoted for precisely the same selection and market/line;
    callers must check that identity prior to calling.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    blockers = []
    if not item.selection.strip():
        blockers.append("selection missing")
    if item.offered_american_odds is None or item.opposite_american_odds is None:
        blockers.append("paired same-market prices missing")
    if not item.executable_hard_rock_verified or not item.sportsbook_authorized_in_location:
        blockers.append("authenticated executable legally accessible Hard Rock quote missing")
    if item.executable_quote_at is None:
        blockers.append("executable quote timestamp missing")
    if item.public_quote_at is None:
        blockers.append("public research quote timestamp missing")
    for label, stamp in (("public", item.public_quote_at), ("executable", item.executable_quote_at)):
        if stamp is not None:
            if stamp.tzinfo is None:
                blockers.append(f"{label} quote timestamp missing timezone")
            else:
                age = (now - stamp).total_seconds()
                if not 0 <= age <= max_quote_age_seconds:
                    blockers.append(f"{label} quote stale or future-dated")
    if not item.calibrated_independent_forecast or not item.forecast_source:
        blockers.append("attributable independent calibrated own-model forecast missing")
    if not item.lambda_justification:
        blockers.append("lambda justification missing")
    if item.model_dispersion_points is None or not math.isfinite(item.model_dispersion_points) or item.model_dispersion_points > max_dispersion_points or item.model_dispersion_points < 0:
        blockers.append("model dispersion gate unverified")
    if not item.availability_verified:
        blockers.append("current personnel availability unverified")
    if not item.all_protective_gates_passed:
        blockers.append("one or more protective gates incomplete or failed")
    if item.verified_bankroll is None or not math.isfinite(item.verified_bankroll) or item.verified_bankroll <= 0:
        blockers.append("positive bankroll verification missing")
    if item.proposed_stake is None or not math.isfinite(item.proposed_stake) or item.proposed_stake <= 0:
        blockers.append("valid proposed stake missing")
    if item.p_raw is None or not math.isfinite(item.p_raw) or not 0 <= item.p_raw <= 1:
        blockers.append("valid p_raw missing")
    if item.lam is None or not math.isfinite(item.lam) or not 0 <= item.lam <= 1:
        blockers.append("valid lambda missing")
    if blockers:
        return CertificationResult("NO BET", tuple(blockers))
    try:
        q_market, _ = no_vig_two_way(item.offered_american_odds, item.opposite_american_odds)
        p_adj = adjusted_probability(q_market, item.p_raw, item.lam)
        ev = expected_value_per_unit(p_adj, item.offered_american_odds)
        max_stake = item.verified_bankroll * quarter_kelly_fraction(p_adj, item.offered_american_odds)
    except (ValueError, ZeroDivisionError, OverflowError):
        return CertificationResult("NO BET", ("invalid odds or market calculation",))
    if ev < minimum_ev:
        blockers.append("adjusted EV below original minimum")
    if item.proposed_stake > max_stake:
        blockers.append("proposed stake exceeds quarter-Kelly cap")
    if blockers:
        return CertificationResult("NO BET", tuple(blockers), p_adj, ev, max_stake)
    return CertificationResult("BET", (), p_adj, ev, max_stake)
