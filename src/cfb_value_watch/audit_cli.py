"""CLI gate for external schedulers. Usage:
python -m cfb_value_watch.audit_cli schedule.json reviews.json

Both files contain JSON arrays keyed by game_id. Exit code 2 blocks publication
when ANY FBS fixture is unreviewed or any BET gate is unsupported.
"""
import json
import sys
from pathlib import Path
from .board_audit import audit_board


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("Usage: python -m cfb_value_watch.audit_cli SCHEDULE.json REVIEWS.json", file=sys.stderr)
        return 2
    try:
        schedule = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        reviews = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        if not isinstance(schedule, list) or not isinstance(reviews, list):
            raise ValueError("Schedule and reviews must be JSON arrays")
        audit = audit_board(schedule, reviews)
    except (OSError, ValueError, TypeError) as e:
        print(f"FAIL CLOSED: {e}", file=sys.stderr)
        return 2
    print(f"Board coverage: {audit.reviewed}/{audit.expected}; "
          f"{'COMPLETE' if audit.complete else 'INCOMPLETE'}")
    for issue in audit.issues:
        print(f"{issue.game_id}: {issue.reason}")
    return 0 if audit.complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
