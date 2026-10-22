"""Audit 2024 and 2025 interconference forecast residuals independently."""
from pathlib import Path
import argparse,json
import pandas as pd
from .conference_postseason import CrossConferenceForecast,conference_residual_audit

def run(source:Path,out:Path):
    df=pd.read_csv(source)
    out.mkdir(parents=True,exist_ok=True)
    reports={}
    for season in (2024,2025):
        part=df[df.season==season]
        records=[]
        for g in part.itertuples(index=False):
            records.append(CrossConferenceForecast(
                game_id=str(g.game_id),
                kickoff=pd.Timestamp(g.kickoff).to_pydatetime(),
                forecast_at=pd.Timestamp(g.as_of).to_pydatetime(),
                home_conference=str(g.home_conference),
                away_conference=str(g.away_conference),
                predicted_home_margin=float(g.predicted_home_margin),
                actual_home_margin=float(g.actual_home_margin)))
        reports[str(season)]=conference_residual_audit(records)
    report={"status":"RESEARCH_ONLY_NOT_BET","years":reports,
            "interpretation":"Cross-conference residuals after team+conference network fit. No automatic SEC bonus."}
    (out/"conference_holdout.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="data/network_validation/schedule_network_predictions.csv")
    p.add_argument("--out",default="data/conference_audit")
    a=p.parse_args()
    run(Path(a.source),Path(a.out))
