from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class GateResult:
    name: str
    passed: bool
    lambda_multiplier: float = 1.0
    p_raw_delta: float = 0.0
    stake_cap: str | None = None
    reasons: list[str] = field(default_factory=list)


def defense_availability_coherence(
    *,
    clustered_front7_losses: int = 0,
    clustered_secondary_losses: int = 0,
    opponent_run_strength: bool = False,
    opponent_pass_strength: bool = False,
    replacement_quality_verified: bool = False,
) -> GateResult:
    reasons: list[str] = []
    mult = 1.0
    passed = True

    if clustered_front7_losses >= 2 and opponent_run_strength:
        reasons.append("clustered front-seven losses conflict with opponent rushing strength")
        mult *= 0.70
        passed = replacement_quality_verified
    if clustered_secondary_losses >= 2 and opponent_pass_strength:
        reasons.append("clustered secondary losses conflict with opponent passing strength")
        mult *= 0.70
        passed = passed and replacement_quality_verified

    return GateResult(
        name="Defense Availability Coherence Gate",
        passed=passed,
        lambda_multiplier=mult,
        stake_cap="B" if reasons else None,
        reasons=reasons,
    )


def large_underdog_survival(
    *,
    spread: float,
    credible_offensive_floor: bool,
    sustainable_scoring_path: bool,
    qb_ol_viable: bool,
    severe_havoc_mismatch: bool,
    independent_cover_paths: int,
    favorite_explosive: bool,
    dog_one_dimensional: bool,
) -> GateResult:
    if spread < 10:
        return GateResult("Large-Underdog Survival Gate", True)

    reasons = []
    passed = True
    for ok, label in [
        (credible_offensive_floor, "no credible offensive floor"),
        (sustainable_scoring_path, "no sustainable scoring path"),
        (qb_ol_viable, "QB/OL viability concern"),
        (not severe_havoc_mismatch, "severe havoc/turnover mismatch"),
        (independent_cover_paths >= 2, "fewer than two independent cover paths"),
    ]:
        if not ok:
            passed = False
            reasons.append(label)

    mult = 0.35 if favorite_explosive and dog_one_dimensional else 1.0
    return GateResult(
        "Large-Underdog Survival Gate",
        passed,
        lambda_multiplier=mult,
        stake_cap="B" if passed and mult < 1 else None,
        reasons=reasons,
    )


def favorite_margin_viability(
    *,
    spread: float,
    early_down_efficiency: bool,
    finishing: bool,
    explosive_path: bool,
    qb_ol_viable: bool,
    opponent_backdoor_risk_low: bool,
    discipline_ok: bool,
    turnover_dependent: bool,
    independent_separation_paths: int,
) -> GateResult:
    if spread > -6:
        return GateResult("Favorite Margin Viability Gate", True)
    reasons = []
    checks = [
        (early_down_efficiency, "weak early-down efficiency"),
        (finishing, "drive-finishing concern"),
        (explosive_path, "limited explosive-play path"),
        (qb_ol_viable, "QB/OL concern"),
        (opponent_backdoor_risk_low, "high opponent backdoor risk"),
        (discipline_ok, "penalty/discipline drag"),
        (not turnover_dependent, "margin depends on turnovers/defensive scores"),
    ]
    passed = True
    for ok, label in checks:
        if not ok:
            passed = False
            reasons.append(label)
    if spread <= -8.5 and independent_separation_paths < 2:
        passed = False
        reasons.append("fewer than two independent separation paths")
    return GateResult("Favorite Margin Viability Gate", passed, reasons=reasons)


def offensive_survival_counterbalance(
    *,
    home_underdog: bool,
    clustered_defensive_injuries: bool,
    sustainable_offense: bool,
    ball_security: bool,
    discipline: bool,
    special_teams_field_position: bool,
    late_game_resilience: bool,
    opponent_defensive_weakness: bool,
) -> GateResult:
    """Moderate—not erase—a defensive injury haircut when multiple verified cover paths exist.

    This gate never assumes future turnovers, return TDs, or special-teams scores.
    It only recognizes sustainable pregame evidence that a home dog can score and protect possessions.
    """
    if not (home_underdog and clustered_defensive_injuries):
        return GateResult("Offensive-Survival Counterbalance Gate", True)

    factors = {
        "sustainable offense": sustainable_offense,
        "ball security": ball_security,
        "discipline": discipline,
        "special teams / field position": special_teams_field_position,
        "late-game resilience": late_game_resilience,
        "opponent defensive weakness": opponent_defensive_weakness,
    }
    verified = [name for name, ok in factors.items() if ok]
    passed = len(verified) >= 3
    return GateResult(
        "Offensive-Survival Counterbalance Gate",
        passed=True,
        lambda_multiplier=1.15 if passed else 1.0,
        stake_cap="B+" if passed else None,
        reasons=[f"verified counterbalance factors: {', '.join(verified)}"] if verified else [],
    )


def combine_lambda(base_lambda: float, results: Iterable[GateResult]) -> float:
    lam = base_lambda
    for result in results:
        lam *= result.lambda_multiplier
    return max(0.0, min(1.0, lam))


def universal_underdog_offense(
    *,
    spread: float,
    early_down_sustainable: bool | None,
    qb_ol_viable: bool | None,
    scoring_path_verified: bool | None,
    havoc_mismatch: bool | None,
    ball_security_acceptable: bool | None,
    discipline_acceptable: bool | None,
    opponent_adjusted_evidence: bool | None,
) -> GateResult:
    """Pregame offensive viability for ALL underdogs, including +1.5.

    None means not verified, not a zero. Critical contradictions veto; other
    documented weaknesses shrink lambda. This is a diagnostic, not a model
    probability and never uses postgame information.
    """
    if spread <= 0:
        return GateResult("Universal Underdog Offensive Viability Gate", True)
    critical = {
        "QB/OL viability": qb_ol_viable,
        "sustainable scoring path": scoring_path_verified,
        "opponent-adjusted offensive evidence": opponent_adjusted_evidence,
    }
    reasons = [f"{name} not verified" if value is None else f"{name} failed"
               for name, value in critical.items() if value is not True]
    mult = 1.0
    optional = {
        "early-down sustainability": early_down_sustainable,
        "ball security": ball_security_acceptable,
        "discipline": discipline_acceptable,
    }
    for name, value in optional.items():
        if value is False:
            reasons.append(f"{name} concern")
            mult *= 0.85
        elif value is None:
            reasons.append(f"{name} unknown")
            mult *= 0.93
    if havoc_mismatch is True:
        reasons.append("severe havoc/turnover mismatch")
        mult *= 0.65
    elif havoc_mismatch is None:
        reasons.append("havoc mismatch not verified")
        mult *= 0.93
    return GateResult(
        "Universal Underdog Offensive Viability Gate",
        passed=(not any(value is not True for value in critical.values())
                and havoc_mismatch is not True),
        lambda_multiplier=mult,
        stake_cap="B" if mult < 1 else None,
        reasons=reasons,
    )
