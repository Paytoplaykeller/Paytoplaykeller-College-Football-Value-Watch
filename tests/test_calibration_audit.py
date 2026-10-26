import pytest
from cfb_value_watch.calibration_audit import OutOfSamplePrediction, audit_probabilities


def sample(n=150, market=True):
    return [OutOfSamplePrediction(str(i), .7 if i % 2 else .3, bool(i % 2),
              .5 if market else None) for i in range(n)]


def test_report_is_deterministic_and_never_claims_market_superiority():
    a=audit_probabilities(sample())
    assert a.samples == 150
    assert a.model_brier < a.market_brier
    assert a.market_superiority_verified is False
    assert sum(count for count, _, _ in a.bins) == 150


def test_missing_market_prior_is_explicit():
    a=audit_probabilities(sample(market=False))
    assert a.market_brier is None
    assert a.brier_advantage is None


def test_insufficient_sample_fails_closed():
    with pytest.raises(ValueError, match="Insufficient"):
        audit_probabilities(sample(30))


def test_duplicate_event_blocked():
    xs=sample()
    xs[-1]=xs[0]
    with pytest.raises(ValueError, match="duplicate"):
        audit_probabilities(xs)


def test_bad_probability_blocked():
    xs=sample()
    xs[0]=OutOfSamplePrediction("0",1.2,False,.5)
    with pytest.raises(ValueError, match="Invalid model"):
        audit_probabilities(xs)
