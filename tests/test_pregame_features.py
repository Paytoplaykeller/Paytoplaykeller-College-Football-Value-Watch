from datetime import datetime, timedelta, timezone
from cfb_value_watch.pregame_features import build_pregame_snapshots, AVAILABILITY_FIELDS


def fixtures():
    base=datetime(2024,9,1,tzinfo=timezone.utc)
    games=[]
    plays=[]
    for i in range(5):
        games.append(dict(game_id=i+1, fbs_game=True, completed=True,
                          home_team="A", away_team="B",
                          home_points=21+i, away_points=14,
                          start_date=(base+timedelta(days=7*i)).isoformat(),
                          neutral_site=False))
        plays += [
            dict(game_id=i+1, pos_team="A", def_pos_team="B",rush=True,**{"pass":False},
                 EPA=0.2,firstD_by_poss=True,td_play=False,sack=False,
                 int=False,fumble_vec=False,yds_rushed=15),
            dict(game_id=i+1, pos_team="B", def_pos_team="A",rush=False,**{"pass":True},
                 EPA=-0.2,firstD_by_poss=False,td_play=False,sack=True,
                 int=False,fumble_vec=False,yds_receiving=0)
        ]
    return games,plays


def test_no_future_game_data_can_change_its_own_pregame_features():
    games,plays=fixtures()
    before=build_pregame_snapshots(games,plays,minimum_prior_games=3)
    assert before[0]["bet_now_eligible"] is False
    assert before[3]["features"]["home_off_epa"] == 0.2
    assert set(before[3]["missing_features"]) == set(AVAILABILITY_FIELDS)
    changed=[dict(p) for p in plays]
    changed[-2]["EPA"]=99.0
    after=build_pregame_snapshots(games,changed,minimum_prior_games=3)
    assert before[-1]["features"] == after[-1]["features"]
    assert after[-1]["bet_now_eligible"] is False


def test_no_imputed_availability_or_nonpregame_snapshot():
    games,plays=fixtures()
    rows=build_pregame_snapshots(games,plays,minimum_prior_games=3)
    assert all("home_qb_availability" not in row["features"] for row in rows)
    assert all(datetime.fromisoformat(row["as_of"]) <
               datetime.fromisoformat(row["kickoff"]) for row in rows)
