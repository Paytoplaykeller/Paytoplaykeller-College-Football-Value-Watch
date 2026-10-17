from cfb_value_watch.decision_v5 import Candidate, OffensiveEvidence, decide, rank_candidates
from cfb_value_watch.gates import GateResult


def sample(**overrides):
    data = dict(
        selection="Example market",
        spread=0,
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


def test_sam_houston_style_small_dog_no_longer_bypasses_gate():
    # Synthetic pregame inputs: not a reconstruction of the actual game.
    r = decide(sample(
        selection="Synthetic Sam Houston +1.5",
        spread=1.5,
        offensive_evidence=OffensiveEvidence(
            early_down_sustainable=False,
            qb_ol_viable=True,
            scoring_path_verified=False,
            havoc_mismatch=True,
            ball_security_acceptable=False,
            discipline_acceptable=False,
            opponent_adjusted_evidence=True,
        ),
    ))
    assert r.status == "WATCH"
    assert "Universal Underdog Offensive Viability Gate" in " ".join(r.reasons)


def test_missing_underdog_evidence_blocks_bet():
    assert decide(sample(spread=1.5)).status == "WATCH"
    assert decide(sample(spread=1.5, minutes_to_kickoff=60)).status == "PASS"


def test_verified_small_dog_can_qualify_without_auto_veto():
    evidence = OffensiveEvidence(
        early_down_sustainable=True, qb_ol_viable=True,
        scoring_path_verified=True, havoc_mismatch=False,
        ball_security_acceptable=True, discipline_acceptable=True,
        opponent_adjusted_evidence=True,
    )
    assert decide(sample(spread=1.5, offensive_evidence=evidence)).status == "BET"


def test_minor_underdog_uncertainty_haircuts_not_auto_pass():
    evidence = OffensiveEvidence(
        early_down_sustainable=None, qb_ol_viable=True,
        scoring_path_verified=True, havoc_mismatch=False,
        ball_security_acceptable=True, discipline_acceptable=True,
        opponent_adjusted_evidence=True,
    )
    r = decide(sample(spread=1.5, offensive_evidence=evidence))
    assert r.lambda_used is not None and r.lambda_used < 0.70
    assert r.status in ("BET", "PASS")


def test_indiana_four_point_loss_is_loss_at_plus_three_half():
    from cfb_value_watch.margin_distribution import cover_push_loss
    assert cover_push_loss({-4: 1.0}, 3.5) == (0, 0, 1.0)
    assert cover_push_loss({-4: 1.0}, 4.5) == (1.0, 0, 0.0)


def test_projected_margin_alone_does_not_certify_spread_bet():
    r = decide(sample(market_type="spread", spread=-3.5))
    assert r.status == "WATCH"
    assert "calibrated exact-margin" in " ".join(r.reasons)


def test_exact_distribution_must_match_forecast_probability():
    r = decide(sample(
        market_type="spread", spread=-3.5,
        calibrated_margin_distribution={-4: 0.60, 7: 0.40},
        margin_distribution_attribution="synthetic regression fixture",
    ))
    assert r.status == "WATCH"
    assert "p_raw differs" in " ".join(r.reasons)


def test_duplicate_same_game_exposure_caps_new_stake():
    r = decide(sample(existing_same_event_exposure=39.0))
    assert r.status == "BET"
    assert r.suggested_stake <= 1.0
    assert decide(sample(existing_same_event_exposure=40.0)).status == "PASS"


def test_integer_spread_push_needs_three_way_ev():
    r = decide(sample(market_type="spread", spread=-3.0,
                      calibrated_margin_distribution={-4: 0.2, 3: 0.2, 7: 0.6},
                      margin_distribution_attribution="synthetic regression fixture"))
    assert r.status == "WATCH"
    assert "push probability" in " ".join(r.reasons)
