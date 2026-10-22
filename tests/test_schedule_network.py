from datetime import datetime,timedelta,timezone
import pytest
from cfb_value_watch.schedule_network import NetworkGame,fit_network

T=datetime(2025,10,17,18,tzinfo=timezone.utc)

def game(i,home="KY",away="OU",hconf="SEC",aconf="SEC",h=24,a=17,neutral=False):
    return NetworkGame(f"g{i}",T-timedelta(days=i+10),2025,home,away,
                       hconf,aconf,neutral,h,a)

def test_network_respects_strength_of_opponents_and_venue():
    games=[]
    for i in range(20):
        games.append(game(i,home="KY",away="LSU",h=30,a=20))
        games.append(game(i+100,home="LSU",away="OU",h=35,a=17))
    rating=fit_network(games,T)
    p=rating.project("KY","OU","SEC","SEC",neutral=True)
    assert p["projected_home_margin"]>0
    assert p["home_team_rating"]>p["away_team_rating"]
    assert p["status"]=="RESEARCH_ONLY_NOT_BET"

def test_future_game_does_not_change_ratings():
    history=[game(i,home="KY",away="OU") for i in range(22)]
    base=fit_network(history,T)
    future=NetworkGame("future",T+timedelta(days=1),2025,
                       "OU","KY","SEC","SEC",False,100,0)
    after=fit_network(history+[future],T)
    assert after.team_ratings==base.team_ratings

def test_cross_conference_strength_is_data_driven():
    games=[]
    for i in range(30):
        games.append(game(i,home="SEC"+str(i%3),away="B10"+str(i%3),
                          hconf="SEC",aconf="BIG TEN",h=35,a=14,neutral=True))
    ratings=fit_network(games,T)
    assert ratings.conference_effects["SEC"]>ratings.conference_effects["BIG TEN"]

def test_no_unseen_game_can_be_used():
    with pytest.raises(ValueError,match="Insufficient"):
        fit_network([game(1)],T)

def test_no_duplicate_game_ids():
    with pytest.raises(ValueError,match="Duplicate"):
        fit_network([game(i) for i in range(21)]+[game(1)],T)
