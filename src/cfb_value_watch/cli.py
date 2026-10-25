"""Read-only CLI. JSON provided by a caller is NOT independently authenticated.

This command never returns an actionable BET from self-asserted JSON flags.
It can expose missing evidence but cannot authenticate betting-account offers.
"""
import argparse
import json
import sys
from datetime import datetime, timezone

from .certification import CertificationEvidence, certify_bet


def _date(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def inspect(payload):
    fields = CertificationEvidence.__dataclass_fields__
    unknown = set(payload) - set(fields)
    if unknown:
        return {"status": "NO_BET", "blockers": ["Unknown fields: " + ", ".join(sorted(unknown))]}
    try:
        values = dict(payload)
        values["quote_timestamp"] = _date(values["quote_timestamp"])
        values["evaluated_at"] = _date(values["evaluated_at"])
        evidence = CertificationEvidence(**values)
        result = certify_bet(evidence)
        blockers = list(result.blockers)
        # User-supplied or research JSON has no trusted provenance. It cannot
        # authenticate execution, accepted prices or independent predictions.
        blockers.append("Untrusted JSON: live sportsbook and forecast adapters not authenticated")
        return {
            "status": "NO_BET",
            "research_math_status": result.status,
            "blockers": blockers,
            "research_p_adj": result.p_adj,
            "research_ev": result.ev,
            "research_quarter_kelly_cap": result.quarter_kelly_cap,
        }
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError) as exc:
        return {"status": "NO_BET", "blockers": ["Invalid evidence payload: " + type(exc).__name__]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect untrusted evidence, never authorize wagers")
    parser.add_argument("json_file", help="Path to local research evidence JSON")
    args = parser.parse_args(argv)
    try:
        with open(args.json_file, encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            raise ValueError("Object required")
        report = inspect(payload)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"status": "NO_BET", "blockers": ["Cannot read evidence: " + type(exc).__name__]}
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
