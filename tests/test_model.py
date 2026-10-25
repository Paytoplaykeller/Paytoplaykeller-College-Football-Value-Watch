from cfb_value_watch.model import american_to_break_even, no_vig_two_way, adjusted_probability


def test_break_even_minus_110():
    assert round(american_to_break_even(-110), 6) == round(110 / 210, 6)


def test_no_vig_symmetric():
    a, b = no_vig_two_way(-110, -110)
    assert round(a, 6) == 0.5
    assert round(b, 6) == 0.5


def test_adjusted_probability():
    assert adjusted_probability(0.50, 0.60, 0.35) == 0.535


import pytest
from cfb_value_watch.model import decimal_odds, expected_value_per_unit

@pytest.mark.parametrize("odds,expected", [(150,.4),(550,100/650),(100,.5),(-100,.5),(-170,170/270)])
def test_odds_probability_and_zero_ev(odds, expected):
    assert american_to_break_even(odds) == pytest.approx(expected)
    assert expected_value_per_unit(expected, odds) == pytest.approx(0)

def test_asymmetric_no_vig():
    a,b = no_vig_two_way(150,-170)
    assert a == pytest.approx(.4/(.4+170/270))
    assert a+b == pytest.approx(1)

@pytest.mark.parametrize("odds", [0,50,-50,True,float('nan'),float('inf'),float('-inf'),None,"150"])
def test_invalid_odds_rejected(odds):
    for fn in (american_to_break_even, decimal_odds):
        with pytest.raises(ValueError):
            fn(odds)
