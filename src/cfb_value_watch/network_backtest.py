"""Walk-forward validation of schedule-network power ratings (research only).

Downloads public schedules. For each calendar week, fit ratings using only
games completed before Monday UTC. No same-week final score leaks into ratings.
2024 is validation, 2025 untouched evaluation. Do not fit hyperparameters on 2025.
"""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
from .schedule_network import NetworkGame,fit_network

URL="https://github.com/sportsdataverse/sportsdataverse-data/releases/download/cfb_schedules/cfb_schedules_{year}.parquet"
NEEDED={"game_id","season","start_date","completed","fbs_game","home_id","away_id",
        "home_conference","away_conference","neutral_site","home_points","away_points"}

def read_games():
    frames=[]
    for year in range(2021,2026):
        frame=pd.read_parquet(URL.format(year=year))
        missing=NEEDED-set(frame.columns)
        if missing: raise ValueError(f"{year}: missing {missing}")
        frames.append(frame[list(NEEDED)])
    df=pd.concat(frames,ignore_index=True)
    df=df[(df.completed==True)&(df.fbs_game==True)].copy()
    df["kickoff"]=pd.to_datetime(df.start_date,utc=True,errors="coerce")
    df=df.dropna(subset=["kickoff","home_points","away_points","home_conference","away_conference"])
    if df.game_id.duplicated().any(): raise ValueError("Duplicate game IDs")
    records=[]
    for g in df.itertuples(index=False):
        records.append(NetworkGame(
            game_id=str(g.game_id),kickoff=g.kickoff.to_pydatetime(),
            season=int(g.season),home_id=str(g.home_id),away_id=str(g.away_id),
            home_conference=str(g.home_conference),away_conference=str(g.away_conference),
            neutral=bool(g.neutral_site),home_points=int(g.home_points),
            away_points=int(g.away_points)))
    return records

def week_start(t):
    d=t.astimezone(timezone.utc)
    return (d-timedelta(days=d.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)

def backtest(out:Path):
    out.mkdir(parents=True,exist_ok=True)
    records=read_games()
    test=[g for g in records if g.season in (2024,2025)]
    groups={}
    for g in test:
        groups.setdefault(week_start(g.kickoff),[]).append(g)
    predictions=[]
    for as_of,week in sorted(groups.items()):
        # Only prior games, never current-week results. Each kickoff must be
        # strictly later than the frozen snapshot.
        valid=[g for g in week if g.kickoff>as_of]
        if not valid: continue
        try: ratings=fit_network(records,as_of,min_games=100)
        except ValueError: continue
        for g in valid:
            pred=ratings.project(g.home_id,g.away_id,g.home_conference,
                                 g.away_conference,g.neutral)
            if min(pred["home_games_seen"],pred["away_games_seen"])<3:
                continue
            predictions.append({
                "game_id":g.game_id,"season":g.season,"as_of":as_of.isoformat(),
                "kickoff":g.kickoff.isoformat(),"home_id":g.home_id,
                "away_id":g.away_id,"home_conference":g.home_conference,
                "away_conference":g.away_conference,
                "predicted_home_margin":pred["projected_home_margin"],
                "actual_home_margin":g.home_points-g.away_points,
                "home_games_seen":pred["home_games_seen"],
                "away_games_seen":pred["away_games_seen"],
                "home_conference_effect":pred["conference_effect_home"],
                "away_conference_effect":pred["conference_effect_away"],
            })
        print("as-of",as_of.date(),"forecast games",len(valid),flush=True)
    result=pd.DataFrame(predictions)
    if result.empty: raise ValueError("No predictions generated")
    result.to_csv(out/"schedule_network_predictions.csv",index=False)
    metrics={}
    for year in (2024,2025):
        d=result[result.season==year]
        if len(d)<100:raise ValueError(f"Too few {year} evaluation games: {len(d)}")
        err=d.predicted_home_margin-d.actual_home_margin
        metrics[str(year)]={"n":len(d),"mae":float(np.mean(abs(err))),
                            "rmse":float(np.sqrt(np.mean(err**2))),
                            "bias":float(np.mean(err))}
    report={"status":"RESEARCH_ONLY_NOT_BET",
            "method":"weekly frozen network ridge with shrinkage; 2024 validation, 2025 holdout",
            "metrics":metrics,
            "limitations":["No point-in-time paired sportsbook prices",
                           "No injuries or lineup availability",
                           "Conference estimates confounded by uneven cross-conference schedules",
                           "Not evidence of positive-EV wagers"]}
    (out/"network_validation.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="data/network_validation")
    args=p.parse_args()
    backtest(Path(args.out))
