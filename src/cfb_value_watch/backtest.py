"""Point-in-time audit of frozen, pregame binary forecasts (research only).

No historical data is fabricated. Never derive probabilities from outcomes.
Totals, pushes, and bets with uncertain settlement are excluded rather than guessed.
"""
from datetime import datetime, timezone
from math import log, isfinite
from .model import american_to_break_even

REQUIRED = ("event_id", "kickoff", "forecast_timestamp", "model_revision",
            "model_run_id", "selection", "market", "line", "odds",
            "p_adj", "market_prior", "outcome", "outcome_verified")


def _utc(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("timezone required")
    return d.astimezone(timezone.utc)


def validate_row(row):
    if not isinstance(row, dict) or any(k not in row for k in REQUIRED):
        raise ValueError("incomplete frozen forecast record")
    if not all(isinstance(row[k], str) and row[k].strip() for k in
               ("event_id", "model_revision", "model_run_id", "selection", "market")):
        raise ValueError("missing forecast identity")
    if row["market"] not in ("spreads", "h2h"):
        raise ValueError("unsupported market or push settlement")
    kickoff = _utc(row["kickoff"])
    forecast = _utc(row["forecast_timestamp"])
    if not forecast < kickoff:
        raise ValueError("lookahead or post-kickoff forecast")
    for k in ("p_adj", "market_prior"):
        p = row[k]
        if type(p) not in (int, float) or not isfinite(p) or not 0 < p < 1:
            raise ValueError("invalid frozen probability")
    if type(row["odds"]) is not int or abs(row["odds"]) < 100:
        raise ValueError("invalid American odds")
    if type(row["line"]) not in (int, float) or not isfinite(row["line"]):
        raise ValueError("invalid line")
    if row["outcome_verified"] is not True or type(row["outcome"]) is not int or row["outcome"] not in (0, 1):
        raise ValueError("unverified or nonbinary settlement")


def backtest(rows):
    if not isinstance(rows, list) or not rows:
        return {"status": "BLOCKED", "reason": "No frozen pregame forecasts supplied"}
    seen = set()
    for r in rows:
        validate_row(r)
        identity = (r["event_id"], r["market"], r["selection"], r["line"], r["model_run_id"])
        if identity in seen:
            raise ValueError("duplicate forecast")
        seen.add(identity)
    # Forecasts may be provided only from immutable historical records, with provenance
    # verified by a separate trusted ingestion step; this function cannot verify provenance.
    eps = 1e-12
    n = len(rows)
    brier = sum((r["p_adj"] - r["outcome"]) ** 2 for r in rows) / n
    baseline_brier = sum((r["market_prior"] - r["outcome"]) ** 2 for r in rows) / n
    logloss = -sum(r["outcome"] * log(max(eps, r["p_adj"])) +
                   (1-r["outcome"]) * log(max(eps, 1-r["p_adj"])) for r in rows) / n
    baseline_logloss = -sum(r["outcome"] * log(max(eps, r["market_prior"])) +
                            (1-r["outcome"]) * log(max(eps, 1-r["market_prior"])) for r in rows) / n
    return {"status": "RESEARCH_ONLY_UNVERIFIED_PROVENANCE", "n": n,
            "brier": brier, "baseline_brier": baseline_brier,
            "log_loss": logloss, "baseline_log_loss": baseline_logloss,
            "warning": "Not a production validation; external timestamp/provenance and out-of-sample partitions required"}
