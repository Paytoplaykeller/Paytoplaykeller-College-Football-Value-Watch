"""BET command must work with verified evidence and fail closed otherwise."""
from datetime import datetime, timedelta, timezone
from cfb_value_watch.bet_cli import decision_from_payload
from cfb_value_watch.bet_channel import GATES

T = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
def sample():
    return {
        "selection": "Example +3.5", "event_id": "2026-example",
        "kickoff": (T + timedelta(days=1)).isoformat(),
        "evaluated_at": T.isoformat(),
        "signals": [
            {"name":"2026 independent offensive signal","favors_selection":True,
             "source":"attributable 2026 team data","observed_at":T.isoformat(),"season":2026},
            {"name":"2026 independent defensive signal","favors_selection":True,
             "source":"attributable 2026 opponent data","observed_at":T.isoformat(),"season":2026}],
        "critical_contradiction":False,"already_placed":False,
        "book":"example-verified-book","line":3.5,"odds":-110,"opposite_odds":-110,
        "same_market_verified":True,"quote_at":T.isoformat(),
        "executable_quote_verified":True,"local_access_verified":True,
        "forecast_source":"independently calibrated 2026 own model",
        "independent_2026_forecast_verified":True,"p_raw":0.64,
        "lambda":0.8,"lambda_rationale":"out-of-sample calibration and uncertainty",
        "dispersion":1.0,"critical_availability_verified":True,"matchup_verified":True,
        "gates":{g:True for g in GATES},"available_bankroll":1000.0,
        "existing_exposure":0.0,"proposed_stake":10.0
    }

def test_complete_verified_evidence_reaches_manual_bet():
    outcome=decision_from_payload(sample())
    assert outcome["decision"]=="BET"
    assert outcome["manual_only"] and outcome["wager_placed"] is False
    assert outcome["ev"] > .04

def test_public_odds_not_executable():
    payload=sample()
    payload["executable_quote_verified"]=False
    assert decision_from_payload(payload)["decision"]=="NO BET"

def test_missing_forecast_fails_closed():
    payload=sample()
    del payload["p_raw"]
    assert decision_from_payload(payload)["decision"]=="NO BET"

def test_mismatched_or_failed_gate_fails_closed():
    payload=sample()
    payload["gates"]["defense_availability"]=False
    assert decision_from_payload(payload)["decision"]=="NO BET"

def test_falsely_missing_price_fails_closed():
    payload=sample()
    payload["opposite_odds"]=None
    assert decision_from_payload(payload)["decision"]=="NO BET"

def test_quote_too_old_fails_closed():
    payload=sample()
    payload["quote_at"]=(T-timedelta(hours=1)).isoformat()
    assert decision_from_payload(payload)["decision"]=="NO BET"
