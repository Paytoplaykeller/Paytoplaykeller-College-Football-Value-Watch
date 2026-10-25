"""Regression guards against nonfinite betting prices and confidence leaks."""
import math
import pytest

from cfb_value_watch.model import (
    american_to_break_even, decimal_odds, adjusted_probability,
    expected_value_per_unit, full_kelly_fraction,
)
from cfb_value_watch.gates import GateResult, combine_lambda


@pytest.mark.parametrize("odds", [0, -99, 99, -10, 20, True, 101.5, float("nan")])
def test_invalid_american_odds_are_rejected(odds):
    with pytest.raises(ValueError):
        american_to_break_even(odds)
    with pytest.raises(ValueError):
        decimal_odds(odds)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), -0.01, 1.01, True])
def test_invalid_raw_probabilities_rejected(value):
    for args in ((value, .5, .5), (.5, value, .5), (.5, .5, value)):
        with pytest.raises(ValueError):
            adjusted_probability(*args)
    with pytest.raises(ValueError):
        expected_value_per_unit(value, -110)
    with pytest.raises(ValueError):
        full_kelly_fraction(value, -110)


@pytest.mark.parametrize("mult", [1.15, -0.1, float("nan"), float("inf"), True])
def test_invalid_gate_confidence_multiplier_is_not_clamped_up(mult):
    with pytest.raises(ValueError):
        combine_lambda(.7, [GateResult("invalid", True, lambda_multiplier=mult)])


@pytest.mark.parametrize("base", [float("nan"), float("-inf"), 1.1, -0.1])
def test_invalid_base_confidence_is_rejected(base):
    with pytest.raises(ValueError):
        combine_lambda(base, [])


def test_valid_haircut_never_raises_confidence():
    assert combine_lambda(.8, [GateResult("uncertainty", True, lambda_multiplier=.6)]) == pytest.approx(.48)
    assert 0 <= adjusted_probability(.5,.6,.7) <= 1
