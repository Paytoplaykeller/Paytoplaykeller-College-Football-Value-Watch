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
