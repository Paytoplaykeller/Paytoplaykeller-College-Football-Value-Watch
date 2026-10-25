from datetime import datetime,timedelta,timezone
import pandas as pd
import pytest
from cfb_value_watch.weekly_power_report import finished,cross_conference_results,generate

NOW=datetime(2026,10,19,13,tzinfo=timezone.utc)

def test_finish_cutoff():
    df=pd.DataFrame([
        {"kickoff":pd.Timestamp(NOW-timedelta(hours=2)),"completed":True,
         "home_points":4,"away_points":2},
        {"kickoff":pd.Timestamp(NOW-timedelta(hours=7)),"completed":True,
         "home_points":4,"away_points":2}
    ])
    assert len(finished(df,NOW))==1

def test_cross_conference_wins():
    df=pd.DataFrame([
        {"home_conference":"SEC","away_conference":"Big Ten",
         "home_points":15,"away_points":21},
        {"home_conference":"Big Ten","away_conference":"SEC",
         "home_points":10,"away_points":24}
    ])
    report=cross_conference_results(df)
    assert report["raw_records"]["SEC"]["wins"]==1
    assert report["raw_records"]["Big Ten"]["wins"]==1

def test_stale_data_blocks_update():
    df=pd.DataFrame([{"kickoff":pd.Timestamp(NOW-timedelta(days=20)),
                      "completed":True,"home_points":6,"away_points":2}])
    with pytest.raises(ValueError,match="stale"):
        generate(df,NOW)


def test_weekly_snapshot_ignores_future_game_score():
    rows=[]
    for i in range(251):
        h=i%10
        a=(i+1)%10
        kickoff=(NOW-timedelta(days=75)+timedelta(hours=i%120)
                 if i<230 else NOW-timedelta(days=2)+timedelta(minutes=i-230))
        if i==250:
            kickoff=NOW+timedelta(days=5)
        rows.append({
            "game_id":str(i),"season":2026,"kickoff":pd.Timestamp(kickoff),
            "start_date":kickoff.isoformat(),"completed":True,"fbs_game":True,
            "home_id":str(h),"away_id":str(a),
            "home_team":f"Team{h}","away_team":f"Team{a}",
            "home_conference":"SEC" if h<5 else "Big Ten",
            "away_conference":"SEC" if a<5 else "Big Ten",
            "home_points":24,"away_points":17,"neutral_site":False
        })
    df=pd.DataFrame(rows)
    first=generate(df,NOW)
    assert first["data_coverage"]["current_season_fbs_completed_games"]==250
    assert len(first["teams"])==10
    assert first["upcoming_games"][0]["status"]=="RESEARCH_ONLY_NOT_BET"
    df.loc[df.game_id=="250","home_points"]=100
    second=generate(df,NOW)
    assert first["teams"]==second["teams"]
