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

from cfb_value_watch.bet_channel import qualify_2026_selection

def test_research_qualified_without_bankroll_or_executable_offer():
    x=replace(sample(),available_bankroll=None,existing_exposure=None,
              proposed_stake=None,executable_quote_verified=False,local_access_verified=False)
    result=qualify_2026_selection(x)
    assert result.status == "BET_QUALIFIED_RESEARCH"
    assert "No stake authorized" in result.instruction

def test_research_qualification_rejects_missing_probability():
    assert qualify_2026_selection(replace(sample(),p_raw=None)).status == "REVIEW"

def test_research_qualification_rejects_failed_gate():
    assert qualify_2026_selection(replace(sample(),gates={})).status == "REVIEW"

def test_research_qualification_rejects_negative_ev():
    assert qualify_2026_selection(replace(sample(),p_raw=.45)).status == "PASS"

def test_research_qualification_does_not_change_executable_bet_requirements():
    x=replace(sample(),available_bankroll=None)
    assert evaluate(x).status == "NO BET"
