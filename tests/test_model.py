from cfb_value_watch.model import american_to_break_even, no_vig_two_way, adjusted_probability


def test_break_even_minus_110():
    assert round(american_to_break_even(-110), 6) == round(110 / 210, 6)


def test_no_vig_symmetric():
    a, b = no_vig_two_way(-110, -110)
    assert round(a, 6) == 0.5
    assert round(b, 6) == 0.5


def test_adjusted_probability():
    assert adjusted_probability(0.50, 0.60, 0.35) == 0.535


def test_positive_american_odds_break_even():
    # +200 requires a 1/3 win probability, not 2/3.
    assert round(american_to_break_even(200), 8) == round(1 / 3, 8)


def test_asymmetric_no_vig_market():
    # +200 and -300 should normalize to 30.77% / 69.23%.
    a, b = no_vig_two_way(200, -300)
    assert round(a, 6) == round((1/3) / (1/3 + 3/4), 6)
    assert round(a + b, 8) == 1.0
