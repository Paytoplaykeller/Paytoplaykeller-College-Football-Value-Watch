from datetime import datetime,timedelta,timezone
from dataclasses import replace
from cfb_value_watch.lean_2026 import LeanCandidate,SeasonSignal
from cfb_value_watch.bet_channel import BetEvidence,GATES,evaluate
T=datetime(2026,10,28,20,tzinfo=timezone.utc)
def sample():
    c=LeanCandidate("Test +3.5","event",T+timedelta(days=2),T,(
        SeasonSignal("off",True,"source",T),SeasonSignal("def",True,"source",T)))
    return BetEvidence(c,"testbook",3.5,-110,-110,True,T,True,True,"test run",
                       True,.64,.8,"holdout calibration",1.0,True,True,
                       {x:True for x in GATES},1000.,0.,10.)
def test_legitimate_evidence_reaches_bet():
    a=evaluate(sample());assert a.status=="BET" and "Manual only" in a.instruction
def test_public_price_alone_fails():
    assert evaluate(replace(sample(),executable_quote_verified=False)).status=="NO BET"
def test_missing_model_fails():
    assert evaluate(replace(sample(),p_raw=None)).status=="NO BET"
def test_missing_gate_fails():
    assert evaluate(replace(sample(),gates={})).status=="NO BET"
def test_exposure_fails():
    assert evaluate(replace(sample(),proposed_stake=500.)).status=="NO BET"
def test_stale_quote_fails():
    assert evaluate(replace(sample(),quote_at=T-timedelta(hours=2))).status=="NO BET"
