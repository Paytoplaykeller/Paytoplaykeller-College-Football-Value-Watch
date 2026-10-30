"""Read-only manual BET evaluator. Never uploads private tickets or places wagers.

Input is a locally supplied JSON file of attributable evidence; missing or
unverified fields fail closed. The public odds scanner alone cannot fill this.
Usage: python -m cfb_value_watch.bet_cli verified_evidence.json
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
from .lean_2026 import LeanCandidate, SeasonSignal
from .bet_channel import BetEvidence, evaluate, GATES

def timestamp(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    return dt

def decision_from_payload(data):
    """Only explicit verified inputs may permit BET; never invent defaults."""
    try:
        required_booleans = ("critical_contradiction", "already_placed",
            "same_market_verified", "executable_quote_verified",
            "local_access_verified", "independent_2026_forecast_verified",
            "critical_availability_verified", "matchup_verified")
        for name in required_booleans:
            if type(data[name]) is not bool:
                raise ValueError(name + " must be a JSON boolean")
        for name in GATES:
            if type(data["gates"][name]) is not bool:
                raise ValueError("gate " + name + " must be a JSON boolean")
        for signal in data["signals"]:
            if type(signal["favors_selection"]) is not bool:
                raise ValueError("signal direction must be a JSON boolean")
        signals = tuple(SeasonSignal(
            name=s["name"], favors_selection=s["favors_selection"],
            source=s["source"], observed_at=timestamp(s["observed_at"]),
            season=s["season"]) for s in data["signals"])
        lean = LeanCandidate(
            selection=data["selection"], event_id=data["event_id"],
            kickoff=timestamp(data["kickoff"]),
            evaluated_at=timestamp(data["evaluated_at"]),
            signals=signals, critical_contradiction=data["critical_contradiction"],
            already_placed=data["already_placed"])
        e = BetEvidence(
            lean=lean, book=data["book"], line=data["line"],
            odds=data["odds"], opposite_odds=data["opposite_odds"],
            same_market_verified=data["same_market_verified"],
            quote_at=timestamp(data["quote_at"]),
            executable_quote_verified=data["executable_quote_verified"],
            local_access_verified=data["local_access_verified"],
            forecast_source=data["forecast_source"],
            independent_2026_forecast_verified=data["independent_2026_forecast_verified"],
            p_raw=data["p_raw"], lam=data["lambda"],
            lambda_rationale=data["lambda_rationale"],
            dispersion=data["dispersion"],
            critical_availability_verified=data["critical_availability_verified"],
            matchup_verified=data["matchup_verified"],
            gates={name: data["gates"][name] for name in GATES},
            available_bankroll=data["available_bankroll"],
            existing_exposure=data["existing_exposure"],
            proposed_stake=data["proposed_stake"])
        # Do not trust a timestamp or forecast/source field merely because
        # a caller has filled it; verification booleans must be supported by
        # independent provenance before the operator uses this CLI.
        outcome = evaluate(e)
        return {"selection": lean.selection, "decision": outcome.status,
                "reasons": list(outcome.reasons), "p_adj": outcome.p_adj,
                "ev": outcome.ev, "instruction": outcome.instruction,
                "manual_only": True, "wager_placed": False}
    except (KeyError, TypeError, ValueError, OverflowError) as ex:
        return {"selection": data.get("selection", "UNKNOWN") if isinstance(data, dict) else "UNKNOWN",
                "decision": "NO BET", "reasons": ["Missing/invalid verified input: " + str(ex)],
                "manual_only": True, "wager_placed": False}

def main():
    p = argparse.ArgumentParser(description="Evaluate private, locally verified BET evidence")
    p.add_argument("evidence", type=Path)
    args = p.parse_args()
    try:
        data = json.loads(args.evidence.read_text(encoding="utf-8"))
        outcome = decision_from_payload(data)
    except (OSError, ValueError) as ex:
        outcome = {"decision": "NO BET", "reasons": ["Input unavailable: " + str(ex)],
                   "manual_only": True, "wager_placed": False}
    print(json.dumps(outcome, indent=2))

if __name__ == "__main__":
    main()
