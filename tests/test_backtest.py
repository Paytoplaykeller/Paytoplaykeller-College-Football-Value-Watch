from datetime import datetime
import pytest
from cfb_value_watch.backtest import backtest, validate_row


def sample():
    return dict(event_id="synthetic-game", kickoff="2026-10-24T16:00:00Z",
        forecast_timestamp="2026-10-24T12:00:00Z", model_revision="fixture",
        model_run_id="fixture-1", selection="synthetic team", market="h2h",
        line=0.0, odds=-110, p_adj=.6, market_prior=.5,
        outcome=1, outcome_verified=True)


def test_no_records_does_not_claim_validation():
    assert backtest([])["status"] == "BLOCKED"


def test_valid_synthetic_row_calculates_without_production_claim():
    r = backtest([sample()])
    assert r["n"] == 1
    assert r["status"] == "RESEARCH_ONLY_UNVERIFIED_PROVENANCE"
    assert r["brier"] == pytest.approx(.16)
    assert r["baseline_brier"] == pytest.approx(.25)


@pytest.mark.parametrize("field,value", [
    ("forecast_timestamp", "2026-10-24T16:00:01Z"),
    ("forecast_timestamp", "2026-10-24T12:00:00"),
    ("market", "totals"),
    ("p_adj", float("nan")),
    ("market_prior", True),
    ("outcome", 2),
    ("outcome_verified", "yes"),
    ("model_run_id", ""),
])
def test_bad_or_leaky_row_rejected(field,value):
    row = sample()
    row[field] = value
    with pytest.raises(ValueError):
        backtest([row])


def test_duplicate_rows_rejected():
    with pytest.raises(ValueError):
        backtest([sample(), sample()])


def test_incomplete_row_rejected():
    row = sample()
    del row["forecast_timestamp"]
    with pytest.raises(ValueError):
        backtest([row])
