"""Run a pregame-only FBS forecast from attributed historical CSV and target JSON.

Usage:
  python -m cfb_value_watch.forecast_cli --history pregame_history.csv --upcoming target.json

Historical CSV columns: game_id,kickoff,as_of,source,final_home_margin,
closing_home_margin (optional), plus all FEATURES from forecast_v5.py.
Target JSON: game_id,kickoff,as_of,source,features dictionary. No outcomes.
Outputs JSON for research, never a sportsbook BET or stake authorization.
"""
import argparse
import csv
import json
from datetime import datetime
from .forecast_v5 import FEATURES, PregameGame, forecast, ForecastUnavailable


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z","+00:00"))


def load_history(path):
    with open(path,newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    games=[]
    for row in rows:
        games.append(PregameGame(
            game_id=row["game_id"],kickoff=parse_time(row["kickoff"]),
            as_of=parse_time(row["as_of"]),source=row["source"],
            features={k:float(row[k]) for k in FEATURES},
            final_home_margin=int(row["final_home_margin"]),
            closing_home_margin=float(row["closing_home_margin"])
                if row.get("closing_home_margin") else None,
        ))
    return games


def load_upcoming(path):
    with open(path,encoding="utf-8") as f: row=json.load(f)
    return PregameGame(
        game_id=row["game_id"],kickoff=parse_time(row["kickoff"]),
        as_of=parse_time(row["as_of"]),source=row["source"],
        features={k:float(row["features"][k]) for k in FEATURES},
    )


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--history",required=True)
    p.add_argument("--upcoming",required=True)
    args=p.parse_args()
    result=forecast(load_history(args.history),load_upcoming(args.upcoming))
    print(json.dumps({
        "status":"RESEARCH_ONLY_NOT_BET",
        "expected_home_margin":result.expected_home_margin,
        "home_margin_probabilities":result.home_margin_probabilities,
        "validation_count":result.validation_count,
        "test_count":result.test_count,
        "test_mae":result.test_mae,
        "test_home_win_brier":result.test_spread_brier,
        "market_comparison_verified":result.test_beats_market,
        "source":result.source,
    },indent=2))


if __name__=="__main__":
    main()
