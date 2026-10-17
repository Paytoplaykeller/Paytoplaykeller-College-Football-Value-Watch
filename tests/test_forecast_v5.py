from datetime import datetime, timedelta, timezone
import pytest
from cfb_value_watch.forecast_v5 import (
    FEATURES, PregameGame, ForecastUnavailable, forecast
)

START=datetime(2024,1,1,tzinfo=timezone.utc)


def game(i, *, completed=True, features=None):
    kickoff=START+timedelta(days=i*2)
    f={k:float((i%7)*0.02+(j%5)*0.03) for j,k in enumerate(FEATURES)}
    if features is not None: f=features
    return PregameGame(
        game_id=f"g{i}", kickoff=kickoff, as_of=kickoff-timedelta(hours=6),
        source="synthetic pregame fixture", features=f,
        final_home_margin=(i%13)-6 if completed else None
    )


def test_forecast_distribution_is_normalized_and_time_split():
    history=[game(i) for i in range(20)]
    result=forecast(history,game(21,completed=False),
                    minimum_train=8,minimum_calibration=4,minimum_test=4)
    assert abs(sum(result.home_margin_probabilities.values())-1)<1e-9
    assert result.validation_count==4 and result.test_count==4
    assert result.test_beats_market is None
    assert result.test_market_brier is None
    assert 0 <= result.home_cover_probability(-3.5) <= 1
    assert 0 <= result.away_cover_probability(3.5) <= 1


def test_no_training_on_future_game_or_leakage():
    with pytest.raises(ForecastUnavailable):
        forecast([game(i) for i in range(20)],game(19,completed=False),
                 minimum_train=8,minimum_calibration=4,minimum_test=4)


def test_no_forecast_without_historical_data():
    with pytest.raises(ForecastUnavailable):
        forecast([],game(30,completed=False))


def test_no_forecast_if_missing_feature():
    f=game(1).features.copy()
    f.pop("home_qb_availability")
    with pytest.raises(ForecastUnavailable):
        forecast([game(0),game(1,features=f)],game(30,completed=False))


def test_no_forecast_if_snapshot_after_kickoff():
    g=game(0)
    late=PregameGame(g.game_id,g.kickoff,g.kickoff,g.source,g.features,0)
    with pytest.raises(ForecastUnavailable):
        forecast([late],game(30,completed=False))


def test_duplicate_games_rejected():
    history=[game(i) for i in range(20)]+[game(0)]
    with pytest.raises(ForecastUnavailable):
        forecast(history,game(30,completed=False))
