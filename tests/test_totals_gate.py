from dataclasses import replace
import pytest
from cfb_value_watch.totals_gate import TotalsEvidence,total_win_push_loss,totals_blockers
from cfb_value_watch.decision_v5 import Candidate,decide

def evidence(**changes):
    fields=dict(total_line=42.5,side="Over",calibrated_total_distribution={35:.4,50:.6},
                distribution_source="synthetic test fixture",
                possessions_verified=True,both_offenses_sustainable=True,
                qb_ol_availability_verified=True,defensive_matchup_consistent=True,
                weather_verified=True,tempo_and_efficiency_verified=True,
                explosive_dependency_low=True,thesis_consistent=True)
    fields.update(changes)
    return TotalsEvidence(**fields)

def candidate(**changes):
    fields=dict(selection="Example Over 42.5",market_type="total",offered_odds=-110,
                q_market=.5,p_raw=.6,base_lambda=.8,bankroll=1000.,
                model_dispersion_points=1.,critical_availability_verified=True,
                offered_price_verified=True,source_attribution="synthetic",
                minutes_to_kickoff=60,spread=None,totals_evidence=evidence())
    fields.update(changes)
    return Candidate(**fields)

def test_totals_without_evidence_cannot_be_bet():
    r=decide(candidate(totals_evidence=None))
    assert r.status=="PASS"
    assert any("Totals Viability Gate" in x for x in r.reasons)

def test_wisconsin_over_defensive_thesis_contradiction_vetoes():
    r=decide(candidate(totals_evidence=evidence(thesis_consistent=False)))
    assert r.status=="PASS"
    assert any("thesis consistency" in x for x in r.reasons)

def test_high_total_without_both_offenses_vetoes():
    r=decide(candidate(totals_evidence=evidence(total_line=62.5,
        calibrated_total_distribution={50:.4,70:.6},
        both_offenses_sustainable=False)))
    assert r.status=="PASS"

def test_missing_scoring_distribution_vetoes():
    assert decide(candidate(totals_evidence=evidence(
        calibrated_total_distribution=None,distribution_source=None))).status=="PASS"

def test_exact_total_probability_must_match_p_raw():
    r=decide(candidate(p_raw=.7))
    assert r.status=="PASS"
    assert any("p_raw differs" in x for x in r.reasons)

def test_integer_total_push_requires_three_way_ev():
    e=evidence(total_line=42.,calibrated_total_distribution={40:.3,42:.2,50:.5})
    r=decide(candidate(p_raw=.5,totals_evidence=e))
    assert r.status=="PASS"
    assert any("push probability" in x for x in r.reasons)

def test_total_gate_can_pass_on_complete_synthetic_fixture():
    r=decide(candidate())
    assert r.status=="BET"

def test_total_settlement_math():
    assert total_win_push_loss({40:.3,42:.2,50:.5},42,"Over")==(.5,.2,.3)
