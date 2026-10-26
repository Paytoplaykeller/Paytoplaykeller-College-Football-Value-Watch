"""Evaluate a verified JSON evidence package (never a raw odds screen).

Usage: python -m cfb_value_watch.decision_cli evidence.json
Exit 0 for BET; 2 for PASS or incomplete evidence.
All timestamps are ISO 8601 with timezone offsets.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from .decision_engine import evaluate


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: python -m cfb_value_watch.decision_cli evidence.json")
        return 2
    try:
        record = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError("evidence must be a JSON object")
        if isinstance(record.get("quote_time"), str):
            record["quote_time"] = datetime.fromisoformat(record["quote_time"])
        result = evaluate(record)
    except (ValueError, OSError, TypeError, KeyError) as e:
        print(json.dumps({"status": "PASS", "reasons": [str(e)], "approved_stake": 0}))
        return 2
    print(json.dumps({
        "status": result.status,
        "reasons": result.reasons,
        "break_even": result.break_even,
        "q_market": result.market_prior,
        "p_adj": result.p_adj,
        "ev": result.ev,
        "quarter_kelly": result.quarter_kelly,
        "approved_stake_ceiling": result.max_stake,
    }, indent=2))
    return 0 if result.status == "BET" else 2


if __name__ == "__main__":
    raise SystemExit(main())
