"""Build a free, pregame-only scoring baseline from SportsDataverse FBS schedules.

Not the full injury-adjusted v5 forecast; never authorizes BET.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import pandas as pd

URL="https://github.com/sportsdataverse/sportsdataverse-data/releases/download/cfb_schedules/cfb_schedules_{year}.parquet"
COLS=["game_id","season","start_date","completed","fbs_game","home_id","away_id",
      "home_team","away_team","home_points","away_points","neutral_site","start_time_tbd"]
FEATURES=["neutral","home_pf","home_pa","home_margin_prior","away_pf","away_pa","away_margin_prior"]

def build(out: Path):
    out.mkdir(parents=True,exist_ok=True)
    frames=[];manifest=[]
    for year in range(2018,2026):
        url=URL.format(year=year)
        frame=pd.read_parquet(url)
        if set(COLS)-set(frame.columns):
            raise ValueError(f"{year} source missing {set(COLS)-set(frame.columns)}")
        manifest.append({"year":year,"source":url,"rows":len(frame)})
        frames.append(frame[COLS])
        print(f"downloaded {year}: {len(frame)} rows",flush=True)
    games=pd.concat(frames,ignore_index=True)
    games=games[(games.completed==True)&(games.fbs_game==True)&(games.start_time_tbd!=True)].copy()
    games["kickoff"]=pd.to_datetime(games.start_date,utc=True,errors="coerce")
    games=games.dropna(subset=["kickoff","home_points","away_points","home_id","away_id"])
    games=games.sort_values(["kickoff","game_id"])
    if games.game_id.duplicated().any():raise ValueError("Duplicate games")
    past=defaultdict(list);rows=[]
    for g in games.itertuples(index=False):
        t=g.kickoff
        def prior(team):
            history=[r for r in past[team] if r[0]+timedelta(hours=6)<t]
            current=[r for r in history if r[0].year==t.year]
            if len(current)<3:return None
            h=history[-8:]
            return np.mean([v[1:] for v in h],axis=0)
        h=prior(str(g.home_id));a=prior(str(g.away_id))
        if h is not None and a is not None:
            rows.append({"game_id":str(g.game_id),"season":int(g.season),
                         "kickoff":t.isoformat(),"home_team":g.home_team,
                         "away_team":g.away_team,"home_margin":int(g.home_points-g.away_points),
                         "neutral":float(bool(g.neutral_site)),
                         "home_pf":float(h[0]),"home_pa":float(h[1]),
                         "home_margin_prior":float(h[2]),
                         "away_pf":float(a[0]),"away_pa":float(a[1]),
                         "away_margin_prior":float(a[2])})
        hp=int(g.home_points);ap=int(g.away_points)
        past[str(g.home_id)].append((t,hp,ap,hp-ap))
        past[str(g.away_id)].append((t,ap,hp,ap-hp))
    data=pd.DataFrame(rows)
    data.to_csv(out/"pregame_features_2018_2025.csv",index=False)
    train=data[data.season<=2023];cal=data[data.season==2024];test=data[data.season==2025]
    if min(len(train),len(cal),len(test))<100:raise ValueError("Insufficient train/cal/test games")
    x=train[FEATURES].to_numpy(float);y=train.home_margin.to_numpy(float)
    mu=x.mean(0);sd=x.std(0);sd[sd<1e-9]=1
    z=np.column_stack([np.ones(len(x)),(x-mu)/sd])
    reg=np.diag([0.0]+[100.0]*len(FEATURES))
    coef=np.linalg.solve(z.T@z+reg,z.T@y)
    def predict(df):
        a=df[FEATURES].to_numpy(float)
        return np.column_stack([np.ones(len(a)),(a-mu)/sd])@coef
    residual=cal.home_margin.to_numpy(float)-predict(cal)
    forecast=predict(test)
    # Empirical calibrated distribution with 1-point discrete smoothing.
    def win_probability(p):
        count=0.0
        for e in residual:
            for d,w in ((-1,.2),(0,.6),(1,.2)):
                count+=w*(round(p+e)+d>0)
        return count/len(residual)
    p=np.array([win_probability(v) for v in forecast])
    actual=(test.home_margin.to_numpy(float)>0).astype(float)
    report={"status":"RESEARCH_ONLY_NOT_BET","train_n":len(train),
            "calibration_n":len(cal),"test_n":len(test),
            "test_mae":float(np.mean(abs(forecast-test.home_margin.to_numpy(float)))),
            "test_home_win_brier":float(np.mean((p-actual)**2)),
            "baseline_50pct_brier":float(np.mean((.5-actual)**2)),
            "source_manifest":manifest,
            "limitations":["No historical injury availability",
                           "No archived two-sided no-vig odds baseline",
                           "No independently validated betting EV"]}
    (out/"validation_report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!="source_manifest"},indent=2),flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="data/public_history")
    args=parser.parse_args()
    build(Path(args.out))

if __name__=="__main__":main()
