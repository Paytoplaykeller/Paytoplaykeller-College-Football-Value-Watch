from datetime import datetime, timezone
from cfb_value_watch.bet_pipeline import convert_quote_and_forecast
from cfb_value_watch.forecast_v5 import PregameGame, CalibratedForecast


def fixture():
    now = datetime.now(timezone.utc)
    game = PregameGame("game1", now, now, "test data", {})
    pred = CalibratedForecast(
        expected_home_margin=4, home_margin_probabilities={3:0.4, 4:0.6},
        validation_count=180, test_count=180, test_mae=10,
        test_spread_brier=.24, test_market_brier=None, test_beats_market=None,
        training_cutoff="2025-01-01", calibration_cutoff="2025-06-01",
        source="own-model-test"
    )
    quote = dict(event_id="game1", home_team="Home",away_team="Away",
                 market="spreads",selection="away",line=6.5,price=-110,
                 opposite_price=-110,source="user-confirmed",
                 opposite_source="user-confirmed",opposite_market="spreads",opposite_line=-6.5,
                 quote_time=now.isoformat(),executable=True,
                 paired_same_book_same_line=True,
                 confirmation="user_verified_hard_rock")
    evidence = dict(event_id="game1",home_team="Home",away_team="Away")
    return game,pred,quote,evidence


def test_own_forecast_is_bound_to_spread_contract():
    game,pred,quote,evidence=fixture()
    row,errs=convert_quote_and_forecast(game,pred,quote,evidence)
    assert not errs
    assert row["p_raw"] == 1.0  # +6.5 covers all +3/+4 home wins for away
    assert row["forecast_source"] == "own-model-test"


def test_wrong_event_is_rejected():
    g,p,q,e=fixture()
    q["event_id"]="another-game"
    assert convert_quote_and_forecast(g,p,q,e)[0] is None


def test_public_odds_are_never_promoted_to_executable():
    g,p,q,e=fixture()
    q["confirmation"]="public_aggregator"
    assert convert_quote_and_forecast(g,p,q,e)[0] is None


def test_no_total_forecast_without_total_model():
    g,p,q,e=fixture()
    q["market"]="totals"
    assert convert_quote_and_forecast(g,p,q,e)[0] is None


def test_integer_spread_push_is_not_approved_by_binary_ev():
    g,p,q,e=fixture()
    q["line"]=6.0
    q["opposite_line"]=-6.0
    row,errs=convert_quote_and_forecast(g,p,q,e)
    assert row is None
    assert any("push" in error for error in errs)


def test_opposite_market_must_be_observed_and_same_line():
    g,p,q,e=fixture()
    q["opposite_line"]=-7.5
    row,errs=convert_quote_and_forecast(g,p,q,e)
    assert row is None
    assert any("opposite spread" in error for error in errs)


def test_opposite_source_must_match_book():
    g,p,q,e=fixture()
    q["opposite_source"]="other sportsbook"
    row,errs=convert_quote_and_forecast(g,p,q,e)
    assert row is None
    assert any("identical sportsbook" in error for error in errs)
