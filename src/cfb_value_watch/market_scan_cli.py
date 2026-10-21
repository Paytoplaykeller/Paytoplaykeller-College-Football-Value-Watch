"""Read-only hourly FBS market scan. Never certifies BET or accesses wagers."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .odds_intake import fetch_cfb_odds, compare_public_markets, OddsIntakeError


def run_scan(output="research_output/hourly_public_board.json"):
    now = datetime.now(timezone.utc)
    result = {
        "checked_at": now.isoformat(),
        "status": "BLOCKED",
        "decision": "NO BET",
        "research_only": True,
        "hardrock_executable": False,
        "candidates": [],
        "blockers": [],
    }
    try:
        snapshot = fetch_cfb_odds()
        comparisons = compare_public_markets(snapshot, now=now)
        result["candidates"] = comparisons
        result["events_seen"] = len(snapshot["events"])
        result["status"] = "RESEARCH_ONLY"
        result["blockers"] = [
            "Own-model live calibrated forecasts and complete availability not verified",
            "Published sportsbook odds are not authenticated executable Hard Rock prices",
            "No verified bankroll or stake authorization",
        ]
    except OddsIntakeError as exc:
        result["blockers"] = [str(exc)]
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    result = run_scan()
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "events_seen": result.get("events_seen", 0),
        "compared_contracts": len(result["candidates"]),
        "blockers": result["blockers"],
    }, indent=2))


if __name__ == "__main__":
    main()
