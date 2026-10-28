from datetime import datetime, timezone, timedelta
from cfb_value_watch.lean_2026 import SeasonSignal, LeanCandidate, assess_lean

NOW = datetime(2026, 10, 28, 16, tzinfo=timezone.utc)
def item(signals=None):
    if signals is None:
        signals=(
            SeasonSignal("2026 rushing efficiency",True,"team release",NOW),
            SeasonSignal("2026 home efficiency",True,"game log",NOW),
            SeasonSignal("2026 defensive matchup",False,"opponent stats",NOW),
        )
    return LeanCandidate("Example +6.5","event1",NOW+timedelta(days=3),NOW,signals,already_placed=True)

def test_research_lean_available_without_forecast_or_book_authentication():
    x=assess_lean(item())
    assert x.status=="LEAN" and x.certified_bet is False
    assert "no automatic additional exposure" in x.reasons[-1]

def test_missing_evidence_review_not_fictional_bet():
    assert assess_lean(item(())).status=="REVIEW"

def test_2025_signal_rejected():
    s=SeasonSignal("old",True,"source",NOW,2025)
    assert assess_lean(item((s,))).status=="PASS"

def test_unresolved_critical_contradiction_forces_review():
    x=item()
    x=LeanCandidate(x.selection,x.event_id,x.kickoff,x.evaluated_at,x.signals,True)
    assert assess_lean(x).status=="REVIEW"

def test_future_dated_rejected():
    s=SeasonSignal("not yet available",True,"source",NOW+timedelta(days=1))
    assert assess_lean(item((s,))).status=="PASS"
