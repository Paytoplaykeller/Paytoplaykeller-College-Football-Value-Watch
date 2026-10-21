"""Bridge the EXISTING v5 model to evidence-backed BET/PASS approval.

Usage: python -m cfb_value_watch.bet_pipeline --history H.csv --upcoming U.json
       --quote Q.json --evidence E.json

Q.json: event_id, home_team, away_team, market, selection, line,
price, opposite_price, source, quote_time, executable, confirmation.
E.json: availability, gates, lambda, dispersion_points, bankroll and
opposing-case/price-limit metadata required by decision_engine.evaluate.
Public odds are research-only; do not set executable=true for a public feed.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .forecast_cli import load_history, load_upcoming
from .forecast_v5 import forecast, ForecastUnavailable
from .decision_engine import evaluate


def convert_quote_and_forecast(upcoming, prediction, quote, evidence):
    """Bind forecasts to the EXACT requested event, market and line."""
    errors = []
    if quote.get("event_id") != upcoming.game_id:
        errors.append("quote game_id mismatch")
    if evidence.get("event_id") != upcoming.game_id:
        errors.append("evidence game_id mismatch")
    if not quote.get("home_team") or not quote.get("away_team"):
        errors.append("named home and away teams required")
    if evidence.get("home_team") != quote.get("home_team") or evidence.get("away_team") != quote.get("away_team"):
        errors.append("team labels do not match evidence")
    if quote.get("market") != "spreads":
        errors.append("v5 distribution bridge currently supports spreads ONLY")
    side = quote.get("selection")
    if side not in ("home", "away"):
        errors.append("selection must be 'home' or 'away' from named event")
    line = quote.get("line")
    if isinstance(line, bool) or not isinstance(line, (int, float)):
        errors.append("numeric spread required")
    if quote.get("executable") is True and quote.get("confirmation") != "user_verified_hard_rock":
        errors.append("executable quote requires explicit Hard Rock user verification")
    if errors:
        return None, errors
    p_raw = (prediction.home_cover_probability(float(line)) if side == "home"
             else prediction.away_cover_probability(float(line)))
    record = dict(evidence)
    record.update(
        offered_odds=quote.get("price"),
        opposite_odds=quote.get("opposite_price"),
        source=quote.get("source"),
        opposite_source=quote.get("source"),
        executable=(quote.get("executable") is True),
        quote_time=datetime.fromisoformat(quote["quote_time"]),
        no_vig_same_market=quote.get("paired_same_book_same_line") is True,
        forecast_source=prediction.source,
        forecast_timestamp=upcoming.as_of.isoformat(),
        forecast_uses_market_implied_probability=False,
        p_raw=p_raw,
    )
    return record, []


def run(history_path, upcoming_path, quote_path, evidence_path, *, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        upcoming = load_upcoming(upcoming_path)
        history = load_history(history_path)
        prediction = forecast(history, upcoming)
        quote = json.loads(Path(quote_path).read_text(encoding="utf-8"))
        evidence = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
        record, errors = convert_quote_and_forecast(upcoming, prediction, quote, evidence)
        if errors:
            return {"status":"PASS", "reasons":errors, "max_stake":0}
        decision = evaluate(record, now=now)
        return {
            "status": decision.status,
            "reasons":list(decision.reasons),
            "expected_home_margin":prediction.expected_home_margin,
            "model_forecast_source":prediction.source,
            "model_test_mae":prediction.test_mae,
            "model_market_superiority_verified":prediction.test_beats_market,
            "p_raw":record["p_raw"], "lambda":record.get("lambda"),
            "q_market":decision.market_prior,
            "break_even":decision.break_even, "p_adj":decision.p_adj,
            "ev":decision.ev,"quarter_kelly":decision.quarter_kelly,
            "max_stake":decision.max_stake,
        }
    except (ValueError, KeyError, TypeError, OSError, ForecastUnavailable) as exc:
        return {"status":"PASS", "reasons":[str(exc)], "max_stake":0}


def main():
    ap=argparse.ArgumentParser()
    for name in ("history","upcoming","quote","evidence"):
        ap.add_argument("--"+name,required=True)
    args=ap.parse_args()
    result=run(args.history,args.upcoming,args.quote,args.evidence)
    print(json.dumps(result,indent=2))
    return 0 if result["status"] == "BET" else 2


if __name__=="__main__":
    raise SystemExit(main())
