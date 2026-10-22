"""Export attributed raw season games without committing private credentials.

Usage: python -m cfb_value_watch.data_cli --years 2023 2024 2025 --out data_raw.json
Requires CFBD_API_KEY. Does not synthesize missing EPA or injury features.
"""
import argparse
import json
from pathlib import Path
from .cfbd_intake import historical_games, CFBDataError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    try:
        result = historical_games(tuple(args.years))
    except CFBDataError as err:
        print(json.dumps({"status": "DATA_UNAVAILABLE", "reason": str(err)}))
        return 2
    Path(args.out).write_text(json.dumps(result), encoding="utf-8")
    count = sum(len(x["records"]) for x in result)
    print(json.dumps({"status": "RAW_DATA_SAVED", "games": count,
                      "historical_features_validated": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
