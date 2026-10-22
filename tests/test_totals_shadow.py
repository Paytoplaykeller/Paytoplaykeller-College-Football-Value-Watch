import pytest
from cfb_value_watch.totals_shadow import TotalRecord, reliability_report, correlated_under_exposure


def record(idx, p=.6, total=40, line=46.5):
    return TotalRecord(str(idx), "2025-10-01T12:00:00+00:00",
                       "2025-10-02T12:00:00+00:00", p, line, total, "archived pregame forecast")


def test_no_fabricated_calibration_from_one_game():
    result = reliability_report([record(1)])
    assert result["status"] == "INSUFFICIENT_SAMPLE"
    assert result["bet_approved"] is False


def test_correct_brier_for_known_outcomes():
    x = reliability_report([record(1, .8, 40), record(2, .2, 54)], min_samples=2)
    assert x["brier"] == pytest.approx(.04)
    assert x["status"] == "DIAGNOSTIC_ONLY"


def test_reject_postkickoff_prediction():
    x = TotalRecord("1", "2025-10-03T12:00:00+00:00",
                    "2025-10-02T12:00:00+00:00", .6, 46.5, 54, "source")
    with pytest.raises(ValueError, match="prekickoff"):
        reliability_report([x])


def test_reject_push_until_settlement_model():
    with pytest.raises(ValueError, match="Push"):
        reliability_report([record(1, total=46, line=46)])


def test_correlated_unders_do_not_invent_joint_probability():
    result = correlated_under_exposure(20, 10, same_game=True)
    assert result["correlated"] is True
    assert result["joint_loss_probability"] is None
