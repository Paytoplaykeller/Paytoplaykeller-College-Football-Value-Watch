"""v5 decision layer: turn verified research into BET/WATCH/PASS without inventing probabilities.

This module never places wagers. All prices and probabilities must be supplied
by timestamped external research; model agreement and critical availability
must be verified separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from .gates import GateResult, combine_lambda, universal_underdog_offense
from .model import adjusted_probability, expected_value_per_unit, quarter_kelly_fraction
from .margin_distribution import cover_push_loss
from .totals_gate import TotalsEvidence, totals_blockers
from .favorite_fragility import FavoriteFragilityEvidence, favorite_fragility_gate

Decision = Literal["BET", "WATCH", "PASS"]


@dataclass(frozen=True)
class OffensiveEvidence:
    early_down_sustainable: bool | None = None
    qb_ol_viable: bool | None = None
    scoring_path_verified: bool | None = None
    havoc_mismatch: bool | None = None
    ball_security_acceptable: bool | None = None
    discipline_acceptable: bool | None = None
    opponent_adjusted_evidence: bool | None = None


@dataclass(frozen=True)
class Candidate:
    selection: str
    offered_odds: int | None
    q_market: float | None
    p_raw: float | None
    base_lambda: float | None
    bankroll: float | None
    model_dispersion_points: float | None
    critical_availability_verified: bool
    offered_price_verified: bool
    source_attribution: str | None
    # Noncritical missing details lower confidence, but do not automatically veto.
    noncritical_uncertainty_multiplier: float = 1.0
    gates: tuple[GateResult, ...] = ()
    minutes_to_kickoff: int | None = None
    existing_exposure: float = 0.0
    stake_cap_dollars: float = 15.0
    spread: float | None = None
    offensive_evidence: OffensiveEvidence | None = None
    market_type: Literal["spread", "moneyline", "total", "other"] = "other"
    calibrated_margin_distribution: dict[int, float] | None = None
    margin_distribution_attribution: str | None = None
    existing_same_event_exposure: float = 0.0
    same_event_cap_dollars: float = 40.0
    totals_evidence: TotalsEvidence | None = None
    favorite_fragility_evidence: FavoriteFragilityEvidence | None = None


@dataclass(frozen=True)
class Recommendation:
    selection: str
    status: Decision
    reasons: tuple[str, ...]
    p_adj: float | None = None
    ev: float | None = None
    lambda_used: float | None = None
    quarter_kelly_ceiling: float = 0.0
    suggested_stake: float = 0.0


def decide(
    candidate: Candidate,
    *,
    minimum_ev: float = 0.04,
    max_dispersion: float = 4.5,
    final_decision_minutes: int = 90,
) -> Recommendation:
    """Evaluate a single market; no executable order or ledger mutation.

    WATCH is for unresolved research before the final checkpoint. At or after
    the final checkpoint, unresolved WATCH candidates become PASS.
    """
    reasons: list[str] = []
    blockers: list[str] = []
    if not candidate.offered_price_verified or candidate.offered_odds is None:
        blockers.append("current executable sportsbook price unverified")
    if not candidate.source_attribution or candidate.p_raw is None:
        blockers.append("attributable raw forecast missing")
    if candidate.q_market is None:
        blockers.append("comparable market prior missing")
    if candidate.base_lambda is None:
        blockers.append("uncertainty weight missing")
    if candidate.model_dispersion_points is None:
        blockers.append("independent model dispersion unmeasured")
    elif candidate.model_dispersion_points > max_dispersion:
        blockers.append("model dispersion exceeds configured ceiling")
    if not candidate.critical_availability_verified:
        blockers.append("critical injury and availability checks incomplete")
    if candidate.bankroll is None or candidate.bankroll <= 0:
        blockers.append("positive bankroll not verified")
    if candidate.noncritical_uncertainty_multiplier < 0 or candidate.noncritical_uncertainty_multiplier > 1:
        blockers.append("invalid noncritical uncertainty multiplier")
    if candidate.existing_exposure < 0 or candidate.stake_cap_dollars < 0 or candidate.existing_same_event_exposure < 0 or candidate.same_event_cap_dollars < 0:
        blockers.append("invalid exposure or stake cap")
    if candidate.market_type == "spread":
        if candidate.calibrated_margin_distribution is None or not candidate.margin_distribution_attribution:
            blockers.append("calibrated exact-margin cover distribution missing")
        elif candidate.spread is not None:
            try:
                cover, push, _ = cover_push_loss(candidate.calibrated_margin_distribution, candidate.spread)
                if push > 1e-9:
                    blockers.append("spread has push probability; binary EV calculation unsupported")
                elif candidate.p_raw is not None and abs(cover - candidate.p_raw) > 1e-6:
                    blockers.append("p_raw differs from exact spread cover probability")
            except ValueError as exc:
                blockers.append(f"invalid margin distribution: {exc}")
    if candidate.market_type == "total":
        blockers.extend(totals_blockers(candidate.totals_evidence, candidate.p_raw))
    if candidate.favorite_fragility_evidence is not None and candidate.market_type == "spread":
        try:
            fragility = favorite_fragility_gate(candidate.favorite_fragility_evidence)
            if fragility["status"] == "INCOMPLETE_RESEARCH":
                blockers.append("favorite margin fragility assessment incomplete")
            elif fragility["flag"] and candidate.spread is not None and candidate.spread < 0:
                blockers.append("favorite margin fragility contradiction requires independent rerating")
        except ValueError as exc:
            blockers.append(f"favorite fragility evidence invalid: {exc}")
    effective_gates = list(candidate.gates)
    if candidate.market_type != "total" and candidate.spread is None:
        blockers.append("market spread not supplied; underdog gate cannot be determined")
    elif candidate.market_type != "total" and candidate.spread is not None and candidate.spread > 0:
        if candidate.offensive_evidence is None:
            blockers.append("universal underdog offensive evidence missing")
        else:
            effective_gates.append(universal_underdog_offense(
                spread=candidate.spread,
                **vars(candidate.offensive_evidence),
            ))
    for gate in effective_gates:
        if not gate.passed:
            blockers.append(f"{gate.name}: {', '.join(gate.reasons) or 'failed'}")
    if blockers:
        final = candidate.minutes_to_kickoff is not None and candidate.minutes_to_kickoff <= final_decision_minutes
        return Recommendation(candidate.selection, "PASS" if final else "WATCH", tuple(blockers))

    assert candidate.q_market is not None
    assert candidate.p_raw is not None
    assert candidate.base_lambda is not None
    assert candidate.offered_odds is not None
    assert candidate.bankroll is not None
    lam = combine_lambda(candidate.base_lambda, effective_gates)
    lam *= candidate.noncritical_uncertainty_multiplier
    p = adjusted_probability(candidate.q_market, candidate.p_raw, lam)
    ev = expected_value_per_unit(p, candidate.offered_odds)
    if ev < minimum_ev:
        reasons.append(f"adjusted EV {ev:.2%} below {minimum_ev:.0%} threshold")
        return Recommendation(candidate.selection, "PASS", tuple(reasons), p, ev, lam)
    kelly = quarter_kelly_fraction(p, candidate.offered_odds)
    stake = min(candidate.bankroll * kelly, candidate.stake_cap_dollars,
                max(0.0, candidate.bankroll - candidate.existing_exposure),
                max(0.0, candidate.same_event_cap_dollars - candidate.existing_same_event_exposure))
    if stake <= 0:
        return Recommendation(candidate.selection, "PASS", ("no remaining authorized exposure",), p, ev, lam, kelly)
    reasons.append("positive adjusted EV; critical checks and gate requirements satisfied")
    return Recommendation(candidate.selection, "BET", tuple(reasons), p, ev, lam, kelly, round(stake, 2))


def rank_candidates(candidates: Sequence[Candidate], limit: int = 5) -> list[Recommendation]:
    """Rank actionable recommendations first; unresolved WATCH candidates next."""
    if limit < 1:
        raise ValueError("limit must be positive")
    recommendations = [decide(c) for c in candidates]
    priority = {"BET": 0, "WATCH": 1, "PASS": 2}
    return sorted(recommendations, key=lambda r: (
        priority[r.status], -(r.ev if r.ev is not None else float("-inf")), r.selection
    ))[:limit]
