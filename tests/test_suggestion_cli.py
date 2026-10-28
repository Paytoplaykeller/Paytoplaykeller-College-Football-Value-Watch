from datetime import datetime,timezone,timedelta
from cfb_value_watch.suggestion_cli import suggest
T=datetime(2026,10,28,16,tzinfo=timezone.utc)
def iso(d):return d.isoformat()
def test_production_suggestion_contract_never_autobets():
    row={"selection":"Example +3.5","event_id":"example","kickoff":iso(T+timedelta(days=1)),
        "signals":[{"name":"2026 form","favors_selection":True,"source":"official","observed_at":iso(T)},
                   {"name":"2026 efficiency","favors_selection":True,"source":"official","observed_at":iso(T)}],
        "public_quote":{"book":"Public","odds":-110,"line":3.5,"as_of":iso(T)}}
    data=suggest({"as_of":iso(T),"candidates":[row]})
    out=data["recommendations"][0]
    assert out["decision"]=="BET SUGGESTION"
    assert out["model_certified_bet"] is False
    assert out["stake_recommendation"] is None
    assert data["mode"]=="RESEARCH_ONLY"
def test_missing_signals_stays_review():
    data=suggest({"as_of":iso(T),"candidates":[{"selection":"X","event_id":"1",
        "kickoff":iso(T+timedelta(days=1)),"signals":[]}]})
    assert data["recommendations"][0]["decision"]=="REVIEW"
