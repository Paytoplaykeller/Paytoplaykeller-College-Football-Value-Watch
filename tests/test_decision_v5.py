from cfb_value_watch.decision_v5 import Candidate, decide, rank_candidates
from cfb_value_watch.gates import GateResult


def sample(**overrides):
    data = dict(
        selection="Example home underdog +7",
        offered_odds=-110,
        q_market=0.50,
        p_raw=0.62,
        base_lambda=0.70,
        bankroll=1000.0,
        model_dispersion_points=2.0,
        critical_availability_verified=True,
        offered_price_verified=True,
        source_attribution="timestamped independent model",
        minutes_to_kickoff=120,
    )
    data.update(overrides)
    return Candidate(**data)


def test_qualifying_bet_has_bounded_stake():
    r = decide(sample())
    assert r.status == "BET"
    assert r.ev is not None and r.ev >= 0.04
    assert 0 < r.suggested_stake <= 15
    assert r.quarter_kelly_ceiling <= 0.25


def test_missing_forecast_watch_then_pass_at_deadline():
    assert decide(sample(p_raw=None, minutes_to_kickoff=120)).status == "WATCH"
    assert decide(sample(p_raw=None, minutes_to_kickoff=60)).status == "PASS"


def test_unverified_critical_qb_is_not_bet():
    assert decide(sample(critical_availability_verified=False)).status == "WATCH"


def test_failed_injury_gate_blocks_bet():
    gate = GateResult("Defense Availability Coherence Gate", False, reasons=["depleted front seven"])
    assert decide(sample(gates=(gate,))).status == "WATCH"


def test_noncritical_uncertainty_reduces_lambda_not_automatic_veto():
    confident = decide(sample())
    uncertain = decide(sample(noncritical_uncertainty_multiplier=0.8))
    assert uncertain.lambda_used < confident.lambda_used
    assert uncertain.p_adj < confident.p_adj


def test_no_invented_probability_or_market_prior():
    assert decide(sample(q_market=None)).status == "WATCH"
    assert decide(sample(source_attribution=None)).status == "WATCH"


def test_model_dispersion_blocks_bet():
    assert decide(sample(model_dispersion_points=6)).status == "WATCH"


def test_exposure_and_stake_caps():
    r = decide(sample(existing_exposure=995))
    assert r.status == "BET"
    assert r.suggested_stake <= 5
    assert decide(sample(existing_exposure=1000)).status == "PASS"


def test_below_threshold_passes():
    assert decide(sample(p_raw=0.53)).status == "PASS"


def test_rank_prioritizes_actionable_bets():
    results = rank_candidates([sample(p_raw=None, selection="Watch"), sample(selection="Bet")])
    assert results[0].selection == "Bet"
