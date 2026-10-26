"""Regression checks: fabricated/partial evidence can never produce BET."""
from datetime import datetime, timezone, timedelta
from cfb_value_watch.decision_engine import evaluate, REQUIRED_GATES, REQUIRED_ROLES


def valid_record():
    now = datetime.now(timezone.utc)
    return dict(
        offered_odds=-110, opposite_odds=-110,
        source="test book offer", opposite_source="test book opposite",
        executable=True, quote_time=now,
        forecast_source="independent-test-forecast", forecast_timestamp=now.isoformat(),
        forecast_uses_market_implied_probability=False, p_raw=0.65, lambda_=0.5,
        dispersion_points=2, available_bankroll=500, bankroll_stake_cap=20,
        availability={r: dict(material=True, checked=True, source="test source", checked_at=now.isoformat()) for r in REQUIRED_ROLES},
        gates={g: dict(applicable=True, passed=True, reason="test-only verified") for g in REQUIRED_GATES},
        price_limit_verified=True, opposing_case_checked=True,
        invalidation_checked=True, no_vig_same_market=True, stake_grade="B",
    )


def test_empty_input_passes_without_bet():
    assert evaluate({}).status == "PASS"


def test_complete_test_fixture_can_clear_math():
    r = valid_record()
    r["lambda"] = r.pop("lambda_")
    d = evaluate(r)
    assert d.status == "BET"
    assert d.ev > 0.04
    assert 0 < d.max_stake <= 15


def test_stale_quotes_fail_closed():
    r = valid_record()
    r["lambda"] = r.pop("lambda_")
    r["quote_time"] -= timedelta(minutes=16)
    assert evaluate(r).status == "PASS"


def test_missing_role_fails_closed():
    r = valid_record()
    r["lambda"] = r.pop("lambda_")
    del r["availability"]["starting_qb"]
    assert evaluate(r).status == "PASS"


def test_invalid_gate_fails_closed():
    r = valid_record()
    r["lambda"] = r.pop("lambda_")
    r["gates"]["large_underdog_survival"]["passed"] = False
    assert evaluate(r).status == "PASS"


def test_missing_price_and_forecast_fail_closed():
    r = valid_record()
    r["lambda"] = r.pop("lambda_")
    r["forecast_source"] = ""
    r["executable"] = False
    assert evaluate(r).status == "PASS"


def test_dispersion_and_low_edge_fail():
    r = valid_record()
    r["lambda"] = r.pop("lambda_")
    r["dispersion_points"] = 4.6
    assert evaluate(r).status == "PASS"
    r["dispersion_points"] = 2.0
    r["p_raw"] = 0.51
    assert evaluate(r).status == "PASS"


def test_immaterial_uncertainty_requires_haircut():
    r = valid_record()
    r["lambda"] = r.pop("lambda_")
    r["availability"]["specialists_if_material"] = dict(
        material=False, checked=False, uncertainty_accounted_for=True,
        reason="low snap impact test fixture"
    )
    assert evaluate(r).status == "PASS"
    r["minor_uncertainty_lambda_applied"] = True
    assert evaluate(r).status == "BET"


def test_material_qb_still_blocks():
    r = valid_record()
    r["lambda"] = r.pop("lambda_")
    r["availability"]["starting_qb"]["checked"] = False
    r["minor_uncertainty_lambda_applied"] = True
    assert evaluate(r).status == "PASS"


def test_gate_not_applicable_requires_evidence():
    r = valid_record()
    r["lambda"] = r.pop("lambda_")
    r["gates"]["large_underdog_survival"] = dict(
        applicable=False, reason="favorite selection")
    assert evaluate(r).status == "PASS"
    r["gates"]["large_underdog_survival"]["applicability_evidence"] = "spread -3"
    assert evaluate(r).status == "BET"


def test_unverified_minors_cannot_be_marked_unmaterial_without_reason():
    r = valid_record()
    r["lambda"] = r.pop("lambda_")
    r["availability"]["linebackers"] = dict(material=False, checked=False)
    r["minor_uncertainty_lambda_applied"] = True
    assert evaluate(r).status == "PASS"


import pytest

@pytest.mark.parametrize("field", ["p_raw","lambda","dispersion_points","available_bankroll","bankroll_stake_cap"])
@pytest.mark.parametrize("bad", [float('nan'),float('inf'),float('-inf'),True,None])
def test_nonfinite_numeric_evidence_blocks(field,bad):
    r=valid_record()
    r["lambda"]=r.pop("lambda_")
    r[field]=bad
    d=evaluate(r)
    assert d.status == "PASS"
    assert d.max_stake == 0
