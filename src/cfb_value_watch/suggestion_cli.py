"""Read-only 2026 suggestion runner.

Input: JSON with `as_of` and `candidates`. Each candidate must contain
`selection`, `event_id`, `kickoff`, `signals`, and optional public quote.
No invented signals, forecast probabilities or executable sportsbook offers.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime
from pathlib import Path
from .lean_2026 import LeanCandidate, SeasonSignal, rank_leans

def iso(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timezone-aware input required")
    return stamp

def suggest(payload: dict) -> dict:
    as_of=iso(payload["as_of"])
    candidates=[]
    evidence={}
    for row in payload.get("candidates", []):
        signals=tuple(SeasonSignal(
            name=x["name"], favors_selection=x["favors_selection"],
            source=x["source"], observed_at=iso(x["observed_at"]),
            season=x.get("season",2026)
        ) for x in row.get("signals",[]))
        candidate=LeanCandidate(
            selection=row["selection"], event_id=row["event_id"],
            kickoff=iso(row["kickoff"]), evaluated_at=as_of,
            signals=signals, critical_contradiction=row.get("critical_contradiction",False),
            already_placed=row.get("already_placed",False)
        )
        candidates.append(candidate)
        evidence[row["selection"]]=row
    results=[]
    for r in rank_leans(tuple(candidates)):
        raw=evidence[r.selection]
        quote=raw.get("public_quote")
        # Research prices are metadata only. No assumption of executable quotes.
        results.append({"selection":r.selection, "decision":r.status,
                        "model_certified_bet":False, "supportive":r.supportive,
                        "opposing":r.opposing, "reasons":list(r.reasons),
                        "public_quote":quote, "manual_only":True,
                        "stake_recommendation":None,
                        "certification_status":"NOT_EVALUATED",
                        "certification_blockers":[
                            "No verified independent calibrated 2026 probability forecast",
                            "No verified no-vig same-market prior and justified lambda",
                            "No complete injury/matchup and risk-gate verification",
                            "No authenticated executable locally accessible sportsbook quote",
                            "No verified available bankroll and quarter-Kelly exposure check"
                        ]})
    return {"as_of":as_of.isoformat(),"season":2026,"mode":"RESEARCH_ONLY",
            "decision":"NO CERTIFIED BET","recommendations":results}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("input",type=Path)
    parser.add_argument("--output",type=Path,default=Path("research_output/2026_suggestions.json"))
    args=parser.parse_args()
    result=suggest(json.loads(args.input.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"decision":result["decision"],"recommendations":len(result["recommendations"])}))
if __name__ == "__main__":
    main()
