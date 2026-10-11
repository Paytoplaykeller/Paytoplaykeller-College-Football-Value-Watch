from cfb_value_watch.model import american_to_break_even, no_vig_two_way, adjusted_probability


def test_break_even_minus_110():
    assert round(american_to_break_even(-110), 6) == round(110 / 210, 6)


def test_no_vig_symmetric():
    a, b = no_vig_two_way(-110, -110)
    assert round(a, 6) == 0.5
    assert round(b, 6) == 0.5


def test_adjusted_probability():
    assert adjusted_probability(0.50, 0.60, 0.35) == 0.535
