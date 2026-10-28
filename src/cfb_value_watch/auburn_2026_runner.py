"""Read-only Auburn vs Ole Miss 2026 forecast runner.

Consumes audited pregame history and target features; never uses market odds as
model forecasts, never places a wager, never exports private ticket data.
"""
import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from .forecast_v5 import PregameGame, forecast, ForecastUnavailable

def parse_game(raw):
    return PregameGame(
        game_id=raw["game_id"],
        kickoff=datetime.fromisoformat(raw["kickoff"]),
        as_of=datetime.fromisoformat(raw["as_of"]),
        source=raw["source"],
        features=raw["features"],
        final_home_margin=raw.get("final_home_margin"),
        closing_home_margin=raw.get("closing_home_margin"),
    )

def evaluate(payload):
    """Returns an evidence-based probability or an explicit NO_BET blocker."""
    try:
        history=[parse_game(x) for x in payload["history"]]
        upcoming=parse_game(payload["upcoming"])
        if "auburn" not in upcoming.game_id.lower() or "ole" not in upcoming.game_id.lower():
            raise ForecastUnavailable("Not the Auburn-Ole Miss matchup")
        if any(x.kickoff.year != 2026 or x.as_of.year != 2026 for x in history):
            raise ForecastUnavailable("Only 2026 historical games permitted")
        if upcoming.kickoff.year != 2026:
            raise ForecastUnavailable("Only 2026 upcoming game permitted")
        if any(g.kickoff >= datetime.fromisoformat("2026-10-28T00:00:00-04:00") for g in history):
            raise ForecastUnavailable("Historical cutoff exceeded; no post-cutoff data allowed")
        result=forecast(history,upcoming)
        prob=result.away_cover_probability(13.5)
        return {"status":"RESEARCH_FORECAST_ONLY", "selection":"Auburn +13.5",
                "p_raw":prob, "validation_count":result.validation_count,
                "test_count":result.test_count, "test_mae":result.test_mae,
                "test_brier":result.test_spread_brier,
                "market_superiority_verified":result.test_beats_market is True,
                "bet_certified":False,
                "blockers":["Authenticated executable offer, current full availability, no-vig comparison, lambda and bankroll gates require separate independent verification"]}
    except (KeyError, TypeError, ValueError, ForecastUnavailable) as exc:
        return {"status":"NO_BET","selection":"Auburn +13.5",
                "p_raw":None,"bet_certified":False,"blockers":[str(exc)]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True,help="Private, attributable 2026 pregame JSON dataset")
    args=parser.parse_args()
    try:
        data=json.loads(Path(args.input).read_text())
        result=evaluate(data)
    except (OSError,ValueError) as exc:
        result={"status":"NO_BET","selection":"Auburn +13.5",
                "p_raw":None,"bet_certified":False,"blockers":[str(exc)]}
    print(json.dumps(result,indent=2))
    return 0 if result["status"]=="RESEARCH_FORECAST_ONLY" else 2

if __name__=="__main__":
    raise SystemExit(main())
