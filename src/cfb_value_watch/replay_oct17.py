"""Frozen pregame replay of Kentucky, BYU and Florida State, Oct 17 2026.

Public schedule data are downloaded at run time, but the network fit uses only
games completed at least six hours before the explicit historical snapshot.
Final outcomes of target games are NEVER inputs. This replay is exploratory:
no probability, market EV or retrospective BET claim is generated.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .schedule_network import NetworkGame, fit_network

URL="https://github.com/sportsdataverse/sportsdataverse-data/releases/download/cfb_schedules/cfb_schedules_{year}.parquet"
AS_OF="2026-10-17T18:00:00-04:00"
TARGETS=(("Kentucky","Oklahoma"),("Notre Dame","BYU"),("Florida State","Miami"))

def normalize_team(name:str)->str:
    import re
    text=re.sub(r"[^a-z0-9]+","",str(name).lower())
    if text in {"miamifl","miamiflorida","miamihurricanes"}: return "miami"
    if text in {"brighamyoung","byucougars"}: return "byu"
    return text
COLS=["game_id","season","start_date","completed","fbs_game","home_id","away_id",
      "home_team","away_team","home_conference","away_conference","neutral_site",
      "home_points","away_points"]

def replay(out:Path, as_of:datetime):
    if as_of.tzinfo is None: raise ValueError("Timezone-aware snapshot required")
    frames=[]
    for year in (2024,2025,2026):
        df=pd.read_parquet(URL.format(year=year))
        missing=set(COLS)-set(df.columns)
        if missing:raise ValueError(f"{year}: missing columns {sorted(missing)}")
        frames.append(df[COLS])
    games=pd.concat(frames,ignore_index=True)
    games=games[games.fbs_game==True].copy()
    games["kickoff"]=pd.to_datetime(games.start_date,utc=True,errors="coerce")
    games=games.dropna(subset=["kickoff","home_id","away_id","home_conference","away_conference"])
    if games.game_id.duplicated().any():raise ValueError("Duplicate schedule game IDs")
    history=[]
    for g in games.itertuples(index=False):
        if g.kickoff >= as_of or not bool(g.completed) or pd.isna(g.home_points) or pd.isna(g.away_points):
            continue
        history.append(NetworkGame(str(g.game_id),g.kickoff.to_pydatetime(),int(g.season),
            str(g.home_id),str(g.away_id),str(g.home_conference),str(g.away_conference),
            bool(g.neutral_site),int(g.home_points),int(g.away_points)))
    ratings=fit_network(history,as_of,min_games=100)
    rows=[]
    games["away_normalized"]=games.away_team.map(normalize_team)
    games["home_normalized"]=games.home_team.map(normalize_team)
    for away,home in TARGETS:
        matches=games[(games.season==2026)&
            (games.away_normalized==normalize_team(away))&
            (games.home_normalized==normalize_team(home))]
        if len(matches)!=1:
            rows.append({"matchup":f"{away} at {home}","status":"NOT_IDENTIFIED",
                         "match_count":len(matches)})
            continue
        g=next(matches.itertuples(index=False))
        if g.kickoff<=as_of:
            rows.append({"matchup":f"{away} at {home}","status":"SNAPSHOT_NOT_PREGAME"})
            continue
        p=ratings.project(str(g.home_id),str(g.away_id),
            str(g.home_conference),str(g.away_conference),bool(g.neutral_site))
        rows.append({"matchup":f"{away} at {home}","game_id":str(g.game_id),
            "kickoff":g.kickoff.isoformat(),"as_of":as_of.isoformat(),
            "home_conference":str(g.home_conference),
            "away_conference":str(g.away_conference),**p,
            "published_pregame_market":"NOT_IMPORTED",
            "critical_injuries":"NOT_RECONSTRUCTED",
            "adjusted_ev":"UNAVAILABLE",
            "decision":"WATCH_RESEARCH_ONLY"})
    report={"status":"RESEARCH_ONLY_NOT_BET","as_of":as_of.isoformat(),
        "source":"SportsDataverse public FBS schedules",
        "training_games":ratings.training_games,
        "matchups":rows,
        "limitations":["Opponent-network margin is not a calibrated cover probability",
          "Pregame injury status and contemporaneous book quotes not ingested",
          "Replay cannot prove a winning strategy from three selected games"]}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2),flush=True)
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--as-of",default=AS_OF)
    parser.add_argument("--out",default="data/replay_2026_10_17.json")
    args=parser.parse_args()
    replay(Path(args.out),datetime.fromisoformat(args.as_of.replace("Z","+00:00")))
