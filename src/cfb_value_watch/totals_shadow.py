"""Shadow-only totals calibration and correlated-outcome diagnostics.

No live wager authorization. Takes timestamped PREKICKOFF forecast probabilities
and actual settled scoring outcomes from independent historical holdout games.
Does not derive totals probabilities from spread forecasts or edit existing code.
"""
from dataclasses import dataclass
from math import log, isfinite
from collections import defaultdict


@dataclass(frozen=True)
class TotalRecord:
    game_id: str
    prediction_time: str
    kickoff_time: str
    probability_under: float
    line: float
    final_total: int
    source: str


def validate(records):
    from datetime import datetime
    ids = set()
    for row in records:
        if not row.game_id or not row.source or row.game_id in ids:
            raise ValueError("Missing/duplicate game identifier or source")
        ids.add(row.game_id)
        issued = datetime.fromisoformat(row.prediction_time.replace("Z", "+00:00"))
        kickoff = datetime.fromisoformat(row.kickoff_time.replace("Z", "+00:00"))
        if issued.tzinfo is None or kickoff.tzinfo is None or issued >= kickoff:
            raise ValueError("Forecast must have documented prekickoff timestamp")
        if not isfinite(row.probability_under) or not 0 <= row.probability_under <= 1:
            raise ValueError("Invalid under probability")
        if not isfinite(row.line) or row.line <= 0 or isinstance(row.final_total, bool) or not isinstance(row.final_total, int):
            raise ValueError("Invalid scoring contract or final total")
        if row.final_total == row.line:
            raise ValueError("Push-capable totals require three-outcome calibration")
    return True


def reliability_report(records, bins=10, min_samples=200):
    """Diagnostics only; never return a calibrated probability or BET."""
    rows = list(records)
    validate(rows)
    if bins < 2 or min_samples < 1:
        raise ValueError("Invalid calibration settings")
    grouped = defaultdict(list)
    scores = []
    log_losses = []
    for row in rows:
        actual = float(row.final_total < row.line)
        probability = row.probability_under
        idx = min(bins - 1, int(probability * bins))
        grouped[idx].append((probability, actual))
        scores.append((probability - actual) ** 2)
        clipped = max(1e-12, min(1 - 1e-12, probability))
        log_losses.append(-(actual * log(clipped) + (1 - actual) * log(1 - clipped)))
    summary = [
        {"bin": i, "count": len(grouped[i]),
         "mean_forecast": sum(x for x, _ in grouped[i]) / len(grouped[i]),
         "actual_under_rate": sum(y for _, y in grouped[i]) / len(grouped[i])}
        for i in range(bins) if grouped[i]
    ]
    return {"status": "DIAGNOSTIC_ONLY" if len(rows) >= min_samples else "INSUFFICIENT_SAMPLE",
            "count": len(rows),
            "brier": sum(scores) / len(scores) if scores else None,
            "log_loss": sum(log_losses) / len(log_losses) if log_losses else None,
            "reliability_bins": summary,
            "bet_approved": False}


def correlated_under_exposure(full_game_under, team_under, *, same_game):
    """Flag shared downside without fabricating their joint probability."""
    if not same_game:
        return {"correlated": False, "joint_loss_probability": None}
    if full_game_under <= 0 or team_under <= 0:
        raise ValueError("Stake or modeled exposure must be positive")
    return {"correlated": True, "joint_loss_probability": None,
            "note": "Joint loss must be estimated from paired point-in-time historical outcomes"}
