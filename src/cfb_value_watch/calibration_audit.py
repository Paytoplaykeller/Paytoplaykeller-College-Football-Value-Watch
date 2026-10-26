"""Auditable calibration diagnostics for genuine held-out pregame predictions.

Do not run on in-sample forecasts, postgame features, or market priors relabeled
as forecasts. This module does not generate or certify any wager.
"""
from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Sequence


@dataclass(frozen=True)
class OutOfSamplePrediction:
    event_id: str
    model_probability: float
    covered: bool
    # Same-market no-vig *pregame* prior, if independently sourced.
    market_probability: float | None = None


@dataclass(frozen=True)
class CalibrationAudit:
    samples: int
    model_brier: float
    market_brier: float | None
    brier_advantage: float | None
    expected_calibration_error: float
    bins: tuple[tuple[int, float, float], ...]
    market_superiority_verified: bool


def audit_probabilities(
    records: Sequence[OutOfSamplePrediction],
    *,
    min_samples: int = 150,
    bin_count: int = 10,
) -> CalibrationAudit:
    if len(records) < min_samples:
        raise ValueError("Insufficient independent out-of-sample predictions")
    if not 2 <= bin_count <= 100:
        raise ValueError("Invalid calibration bin count")
    ids = [r.event_id for r in records]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("Missing/duplicate event identifiers")
    for r in records:
        if not isfinite(r.model_probability) or not 0 <= r.model_probability <= 1:
            raise ValueError("Invalid model probability")
        if type(r.covered) is not bool:
            raise ValueError("Outcomes must be verified booleans")
        if r.market_probability is not None and (
            not isfinite(r.market_probability) or not 0 <= r.market_probability <= 1
        ):
            raise ValueError("Invalid paired market probability")
    def brier(ps):
        return sum((p - float(r.covered))**2 for p,r in zip(ps,records)) / len(records)
    model_brier=brier([r.model_probability for r in records])
    all_markets=all(r.market_probability is not None for r in records)
    market_brier=brier([r.market_probability for r in records]) if all_markets else None
    grouped=[[] for _ in range(bin_count)]
    for r in records:
        index=min(bin_count-1,int(r.model_probability*bin_count))
        grouped[index].append(r)
    bins=[]
    ece=0.0
    for group in grouped:
        if not group:
            bins.append((0,0.0,0.0))
            continue
        confidence=sum(r.model_probability for r in group)/len(group)
        observed=sum(r.covered for r in group)/len(group)
        bins.append((len(group), confidence, observed))
        ece += len(group)/len(records)*abs(confidence-observed)
    advantage=(market_brier-model_brier) if market_brier is not None else None
    # Point estimate alone cannot establish significance, so never claim a
    # verified market edge based solely on this diagnostic.
    return CalibrationAudit(len(records),model_brier,market_brier,advantage,
                            ece,tuple(bins),False)
