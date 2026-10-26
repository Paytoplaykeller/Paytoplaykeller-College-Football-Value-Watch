"""Fail-closed pricing evaluator for independently sourced, timestamped game inputs.

This module never fetches or fabricates odds, forecasts, injuries or schedules.
All probability forecasts must be independently produced and attributed.
"""
from dataclasses import dataclass
import math
from datetime import datetime, timezone
from typing import Mapping
from .model import (
    american_to_break_even, no_vig_two_way, adjusted_probability,
    expected_value_per_unit, quarter_kelly_fraction,
)

REQUIRED_ROLES = (
    "starting_qb", "backup_qb_if_relevant", "offensive_line",
    "running_backs", "receivers_tight_ends", "pass_rush",
    "linebackers", "secondary", "specialists_if_material", "discipline",
)
REQUIRED_GATES = (
    "large_underdog_survival", "favorite_margin_viability",
    "defense_availability_coherence", "thesis_consistency",
    "correlated_injury", "offensive_survival_counterbalance",
)
STAKE_CAPS = {"B": 15, "B_PLUS": 20, "A_MINUS": 30, "A": 40}


@dataclass(frozen=True)
class Decision:
    status: str
    reasons: tuple[str, ...]
    break_even: float | None = None
    market_prior: float | None = None
    p_adj: float | None = None
    ev: float | None = None
    quarter_kelly: float | None = None
    max_stake: float = 0


def evaluate(record: Mapping, *, now: datetime | None = None) -> Decision:
    """Return BET only for documented, internally consistent evidence.

    Input is a downstream adapter's evidence package, NOT a raw odds feed.
    A missing input always blocks a bet; numeric zero is valid where meaningful.
    """
    now = now or datetime.now(timezone.utc)
    errors = []
    def number(key, lo=None, hi=None):
        value = record.get(key)
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            errors.append(f"missing/invalid {key}")
            return None
        if (lo is not None and value < lo) or (hi is not None and value > hi):
            errors.append(f"out-of-range {key}")
            return None
        return float(value)

    odds = record.get("offered_odds")
    opposite = record.get("opposite_odds")
    if not all(isinstance(v, int) and not isinstance(v, bool) and abs(v) >= 100 for v in (odds, opposite)):
        errors.append("verified two-way American odds required")
    if not record.get("source") or not record.get("opposite_source"):
        errors.append("book and opposing-market source required")
    if record.get("executable") is not True:
        errors.append("offer not confirmed executable")
    ts = record.get("quote_time")
    if not isinstance(ts, datetime) or ts.tzinfo is None:
        errors.append("timezone-aware quote timestamp required")
    elif not 0 <= (now-ts).total_seconds() <= 900:
        errors.append("quote older than 15 minutes or future")
    if not record.get("forecast_source") or not record.get("forecast_timestamp"):
        errors.append("attributable, timestamped independent forecast required")
    else:
        try:
            ft = datetime.fromisoformat(record["forecast_timestamp"])
            if ft.tzinfo is None or not 0 <= (now-ft).total_seconds() <= 86400:
                errors.append("forecast stale or timestamp invalid")
        except (TypeError, ValueError):
            errors.append("forecast timestamp invalid")
    if record.get("forecast_uses_market_implied_probability") is not False:
        errors.append("forecast independence unverified")
    raw = number("p_raw", 0, 1)
    lam = number("lambda", 0, 1)
    dispersion = number("dispersion_points", 0)
    bank = number("available_bankroll", 0)
    stake_cap = number("bankroll_stake_cap", 0)
    minor_uncertainties = []
    for role in REQUIRED_ROLES:
        detail = (record.get("availability") or {}).get(role)
        if not isinstance(detail, dict):
            errors.append(f"availability assessment missing: {role}")
            continue
        material = detail.get("material")
        if not isinstance(material, bool):
            errors.append(f"materiality missing: {role}")
            continue
        if detail.get("checked") is not True:
            if material:
                errors.append(f"material availability evidence missing: {role}")
            elif detail.get("uncertainty_accounted_for") is True and detail.get("reason"):
                minor_uncertainties.append(role)
            else:
                errors.append(f"unaccounted minor availability uncertainty: {role}")
            continue
        if not detail.get("source") or not detail.get("checked_at"):
            errors.append(f"availability evidence incomplete: {role}")
            continue
        try:
            checked = datetime.fromisoformat(detail["checked_at"])
            if checked.tzinfo is None or not 0 <= (now-checked).total_seconds() <= 86400:
                errors.append(f"availability evidence stale: {role}")
        except (TypeError, ValueError):
            errors.append(f"availability timestamp invalid: {role}")
    # The caller must demonstrate that every unverified minor item has already
    # reduced lambda. We do not choose a haircut or invent its magnitude.
    if minor_uncertainties and record.get("minor_uncertainty_lambda_applied") is not True:
        errors.append("minor uncertainty not incorporated into lambda")
    for gate in REQUIRED_GATES:
        result = (record.get("gates") or {}).get(gate)
        if not isinstance(result, dict) or not result.get("reason"):
            errors.append(f"gate assessment missing: {gate}")
        elif result.get("applicable") is False:
            if not result.get("applicability_evidence"):
                errors.append(f"gate nonapplicability unsubstantiated: {gate}")
        elif result.get("applicable") is True:
            if result.get("passed") is not True:
                errors.append(f"gate failed: {gate}")
        else:
            errors.append(f"gate applicability unknown: {gate}")
    if record.get("price_limit_verified") is not True:
        errors.append("max playable price/line not independently verified")
    if record.get("opposing_case_checked") is not True:
        errors.append("strongest opposing case not documented")
    if record.get("invalidation_checked") is not True:
        errors.append("invalidation conditions missing")
    if record.get("no_vig_same_market") is not True:
        errors.append("two sides of same market not verified")
    if errors:
        return Decision("PASS", tuple(errors))
    market, _ = no_vig_two_way(odds, opposite)
    adj = adjusted_probability(market, raw, lam)
    ev = expected_value_per_unit(adj, odds)
    kelly = quarter_kelly_fraction(adj, odds)
    if dispersion > 4.5:
        errors.append("model dispersion exceeds 4.5 points")
    if ev < 0.04:
        errors.append("adjusted EV below 4%")
    if kelly <= 0 or bank <= 0 or stake_cap <= 0:
        errors.append("no permitted bankroll stake")
    grade = record.get("stake_grade")
    if grade not in STAKE_CAPS:
        errors.append("invalid stake grade")
    stake = min(bank * kelly, stake_cap, STAKE_CAPS.get(grade, 0))
    if stake <= 0:
        errors.append("calculated stake is zero")
    return Decision(
        "BET" if not errors else "PASS", tuple(errors),
        american_to_break_even(odds), market, adj, ev, kelly,
        round(stake, 2) if not errors else 0,
    )
