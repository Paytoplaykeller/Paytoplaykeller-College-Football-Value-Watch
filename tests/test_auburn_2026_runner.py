from cfb_value_watch.auburn_2026_runner import evaluate

def test_no_dataset_is_not_bet():
    out=evaluate({})
    assert out["status"]=="NO_BET"
    assert out["p_raw"] is None

def test_empty_history_cannot_make_bet():
    out=evaluate({"history":[],"upcoming":{"game_id":"auburn-ole-miss"}})
    assert out["status"]=="NO_BET"
    assert out["bet_certified"] is False

def test_no_market_probability_is_invented():
    out=evaluate({"history":[],"upcoming":{"game_id":"auburn-ole-miss",
         "kickoff":"2026-10-31T12:45:00-04:00","as_of":"2026-10-28T14:00:00-04:00",
         "source":"unverified","features":{}}})
    assert out["p_raw"] is None
