"""Safety regression coverage for the restored October 17 research baseline.

No predictions, stakes, live odds, credentials, or private tickets are needed.
"""
import math
import pytest
from cfb_value_watch.model import (
    american_to_break_even, no_vig_two_way, adjusted_probability,
    decimal_odds, expected_value_per_unit, full_kelly_fraction,
    quarter_kelly_fraction, BetEvaluation,
)
from cfb_value_watch.gates import (
    defense_availability_coherence, large_underdog_survival,
    favorite_margin_viability, offensive_survival_counterbalance,
    combine_lambda,
)

@pytest.mark.parametrize("odds", [0])
def test_zero_american_odds_rejected_by_every_math_entry_point(odds):
    for fn in (american_to_break_even, decimal_odds):
        with pytest.raises(ValueError, match="zero"):
            fn(odds)
    for fn in (expected_value_per_unit, full_kelly_fraction, quarter_kelly_fraction):
        with pytest.raises(ValueError, match="zero"):
            fn(0.5, odds)

@pytest.mark.parametrize("odds,expected", [(-110, 110/210), (100, 0.5), (200, 1/3), (-200, 2/3)])
def test_break_even_and_decimal_prices_consistent(odds, expected):
    assert american_to_break_even(odds) == pytest.approx(expected)
    assert decimal_odds(odds) == pytest.approx(1/expected)

def test_no_vig_probs_sum_to_one():
    a, b = no_vig_two_way(-115, -105)
    assert 0 < a < 1 and 0 < b < 1
    assert a + b == pytest.approx(1.0)

def test_adjusted_probability_is_market_anchor_and_lambda_bounded():
    assert adjusted_probability(0.5, 0.8, 0) == pytest.approx(0.5)
    assert adjusted_probability(0.5, 0.8, 1) == pytest.approx(0.8)
    with pytest.raises(ValueError):
        adjusted_probability(0.5, 0.8, 1.01)

def test_ev_is_zero_at_exact_break_even_and_kelly_is_nonnegative():
    p = american_to_break_even(-110)
    assert expected_value_per_unit(p, -110) == pytest.approx(0, abs=1e-12)
    assert quarter_kelly_fraction(p, -110) == pytest.approx(0)
    assert quarter_kelly_fraction(0.6, -110) == pytest.approx(full_kelly_fraction(0.6, -110) / 4)

def test_four_percent_ev_guardrail_is_not_assumed_from_book_odds():
    # This tests arithmetic only. The selection gate requires separately verified forecasts.
    e = BetEvaluation("synthetic research fixture", -110, .5, .5, .35)
    assert e.ev < .04
    assert e.quarter_kelly == 0

def test_clustered_defensive_injuries_fail_closed_without_verified_replacements():
    result = defense_availability_coherence(
        clustered_front7_losses=2, opponent_run_strength=True,
        replacement_quality_verified=False)
    assert not result.passed
    assert result.lambda_multiplier == pytest.approx(.7)
    good = defense_availability_coherence(
        clustered_front7_losses=2, opponent_run_strength=True,
        replacement_quality_verified=True)
    assert good.passed

def test_large_underdog_survival_does_not_pass_without_qb_ol():
    result = large_underdog_survival(
        spread=10.5, credible_offensive_floor=True, sustainable_scoring_path=True,
        qb_ol_viable=False, severe_havoc_mismatch=False, independent_cover_paths=2,
        favorite_explosive=False, dog_one_dimensional=False)
    assert not result.passed
    assert any("QB/OL" in reason for reason in result.reasons)

def test_favorite_margin_cannot_depend_on_turnovers():
    result = favorite_margin_viability(
        spread=-8.5, early_down_efficiency=True, finishing=True,
        explosive_path=True, qb_ol_viable=True, opponent_backdoor_risk_low=True,
        discipline_ok=True, turnover_dependent=True, independent_separation_paths=2)
    assert not result.passed

def test_kentucky_lsu_counterbalance_does_not_assume_turnovers_or_return_tds():
    base = dict(home_underdog=True, clustered_defensive_injuries=True,
                sustainable_offense=False, ball_security=True,
                discipline=False, special_teams_field_position=False,
                late_game_resilience=True, opponent_defensive_weakness=False)
    weak = offensive_survival_counterbalance(**base)
    assert weak.lambda_multiplier == 1.0
    strong = offensive_survival_counterbalance(**{**base, "sustainable_offense": True})
    assert strong.lambda_multiplier == pytest.approx(1.15)
    # It mitigates an injury haircut, and never by itself authorizes a prediction or BET.
    injury = defense_availability_coherence(clustered_secondary_losses=2,
        opponent_pass_strength=True, replacement_quality_verified=False)
    assert not injury.passed
    assert combine_lambda(0.5, [injury, strong]) < 0.5

def test_lambda_clamped_to_valid_probability_weight():
    counter = offensive_survival_counterbalance(
        home_underdog=True, clustered_defensive_injuries=True,
        sustainable_offense=True, ball_security=True, discipline=True,
        special_teams_field_position=False, late_game_resilience=False,
        opponent_defensive_weakness=False)
    assert combine_lambda(.98, [counter]) == 1.0
