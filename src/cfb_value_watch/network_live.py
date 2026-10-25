"""As-of schedule-network research for upcoming FBS games.

Fetches public schedules. This is not a sportsbook price, injury report,
calibrated cover probability or BET recommendation.
"""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import argparse,json
import pandas as pd
from .schedule_network import NetworkGame,fit_network

URL="https://github.com/sportsdataverse/sportsdataverse-data/releases/download/cfb_schedules/cfb_schedules_{year}.parquet"
COLS=["game_id","season","start_date","completed","fbs_game","home_id","away_id",
      "home_team","away_team","home_conference","away_conference","neutral_site",
      "home_points","away_points"]

def run(as_of:datetime,output:Path):
    if as_of.tzinfo is None:raise ValueError("as_of must be timezone aware")
    years=range(as_of.year-2,as_of.year+1)
    frames=[]
    for year in years:
        df=pd.read_parquet(URL.format(year=year))
        if set(COLS)-set(df.columns):raise ValueError("Missing source columns")
        frames.append(df[COLS])
    frame=pd.concat(frames,ignore_index=True)
    frame=frame[frame.fbs_game==True].copy()
    frame["kickoff"]=pd.to_datetime(frame.start_date,utc=True,errors="coerce")
    frame=frame.dropna(subset=["kickoff","home_id","away_id","home_conference","away_conference"])
    if frame.game_id.duplicated().any():raise ValueError("Duplicate schedule IDs")
    history=[]
    for g in frame.itertuples(index=False):
        if not g.completed or pd.isna(g.home_points) or pd.isna(g.away_points):
            continue
        history.append(NetworkGame(str(g.game_id),g.kickoff.to_pydatetime(),
            int(g.season),str(g.home_id),str(g.away_id),
            str(g.home_conference),str(g.away_conference),
            bool(g.neutral_site),int(g.home_points),int(g.away_points)))
    ratings=fit_network(history,as_of,min_games=100)
    upcoming=frame[(frame.kickoff>as_of)&(frame.season==as_of.year)].copy()
    output.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    for g in upcoming.itertuples(index=False):
        p=ratings.project(str(g.home_id),str(g.away_id),
            str(g.home_conference),str(g.away_conference),bool(g.neutral_site))
        rows.append({
            "game_id":str(g.game_id),"kickoff":g.kickoff.isoformat(),
            "home":g.home_team,"away":g.away_team,
            "home_conference":g.home_conference,"away_conference":g.away_conference,
            **p,"forecast_at":as_of.isoformat(),
            "hardrock_price":"UNVERIFIED",
            "model_edge":"NOT_ESTABLISHED",
        })
    output.write_text(json.dumps({"as_of":as_of.isoformat(),
        "source":"SportsDataverse public FBS schedules",
        "training_games":ratings.training_games,
        "status":"RESEARCH_ONLY_NOT_BET","games":rows},indent=2))
    print("Upcoming games:",len(rows),"training games:",ratings.training_games,
          "output:",output,flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="data/network_research/upcoming.json")
    args=p.parse_args()
    run(datetime.now(timezone.utc),Path(args.out))
