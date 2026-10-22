import pandas as pd
import pytest
from cfb_value_watch.market_backtest import join_market,measure,wilson_lower


def records():
    network=pd.DataFrame([
        {"game_id":"a","season":2024,"predicted_home_margin":3.0,"actual_home_margin":-2.0},
        {"game_id":"b","season":2025,"predicted_home_margin":-2.0,"actual_home_margin":5.0},
        {"game_id":"c","season":2025,"predicted_home_margin":5.0,"actual_home_margin":1.0},
        {"game_id":"d","season":2025,"predicted_home_margin":1.0,"actual_home_margin":-10.0},
    ])
    betting=pd.DataFrame([
        {"game_id":"a","home_team_spread":-7.5,"odds_source":"summary_pickcenter","game_spread_available":True},
        {"game_id":"b","home_team_spread":3.5,"odds_source":"core_odds_api","game_spread_available":True},
        {"game_id":"c","home_team_spread":-3.5,"odds_source":"default","game_spread_available":True},
        {"game_id":"d","home_team_spread":-7.5,"odds_source":"summary_pickcenter","game_spread_available":True},
    ])
    return network,betting


def test_ats_outcomes_both_home_and_away_underdogs():
    joined,coverage=join_market(*records())
    assert coverage["matched_rows"]==3
    assert dict(zip(joined.game_id,joined.ats_result))=={
        "a":"WIN", "b":"WIN", "d":"WIN"
    }
    assert measure(joined,3.0)["wins"]==2  # a and b only


def test_default_lines_are_not_treated_as_quotes():
    joined,_=join_market(*records())
    assert "c" not in set(joined.game_id)


def test_conflicting_provider_lines_excluded():
    network,betting=records()
    betting=pd.concat([betting,pd.DataFrame([{
        "game_id":"a","home_team_spread":-6.5,
        "odds_source":"core_odds_api","game_spread_available":True
    }])],ignore_index=True)
    joined,coverage=join_market(network,betting)
    assert "a" not in set(joined.game_id)
    assert coverage["conflicting_games_excluded"]==1


def test_wilson_interval_not_naive_win_rate():
    assert wilson_lower(6,10)<.6
    assert wilson_lower(0,0) is None


def test_duplicate_model_games_rejected():
    network,betting=records()
    with pytest.raises(ValueError,match="Duplicate"):
        join_market(pd.concat([network,network.iloc[[0]]]),betting)
