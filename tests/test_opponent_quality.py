from datetime import datetime,timedelta,timezone
import pytest
from cfb_value_watch.opponent_quality import OpponentResult,quality_profile

T=datetime(2026,10,17,20,tzinfo=timezone.utc)
def game(team,opponent,rating,win=True):
    kickoff=T-timedelta(days=7)
    return OpponentResult(team,opponent,kickoff,kickoff-timedelta(days=1),
                          rating,"frozen pregame rating",24 if win else 14,
                          14 if win else 24)

def test_quality_of_wins_differs_from_schedule_strength():
    kentucky=[game("Kentucky","Texas A&M",20),game("Kentucky","LSU",18),
              game("Kentucky","South Alabama",-10)]
    ou=[game("Oklahoma","Texas",24),game("Oklahoma","UTEP",-20),
        game("Oklahoma","New Mexico",-8)]
    k=quality_profile("Kentucky",kentucky,T)
    o=quality_profile("Oklahoma",ou,T)
    assert k["quality_of_wins"]>o["quality_of_wins"]
    assert k["wins"]==o["wins"]==3
    assert k["model_bet_authorized"] is False

def test_missing_frozen_rating_rejected():
    g=game("Kentucky","LSU",18)
    bad=OpponentResult(g.team,g.opponent,g.kickoff,g.kickoff+timedelta(hours=1),
                       g.opponent_rating,g.rating_source,g.points_for,g.points_against)
    with pytest.raises(ValueError):
        quality_profile("Kentucky",[bad],T,min_games=1)

def test_insufficient_games_not_zero_strength():
    assert quality_profile("Kentucky",[game("Kentucky","LSU",18)],T)["status"]=="INSUFFICIENT_EVIDENCE"
