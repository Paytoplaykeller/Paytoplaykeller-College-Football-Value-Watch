"""Calibrate opponent-network blending on 2024; evaluate untouched 2025.

Use exactly matched games. Never select weights on 2025 outcomes.
This validates margin MAE only, not cover probabilities or wagering EV.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd

FEATURES=["neutral","home_pf","home_pa","home_margin_prior",
          "away_pf","away_pa","away_margin_prior"]


def compare(baseline_csv: Path, network_csv: Path, output: Path) -> dict:
    base=pd.read_csv(baseline_csv)
    network=pd.read_csv(network_csv)
    train=base[base.season<=2023]
    if len(train)<1000: raise ValueError("Insufficient historical baseline")
    x=train[FEATURES].to_numpy(float)
    mu=x.mean(axis=0);sigma=x.std(axis=0);sigma[sigma<1e-9]=1
    design=np.column_stack((np.ones(len(x)),(x-mu)/sigma))
    coef=np.linalg.solve(design.T@design+np.diag([0]+[100]*len(FEATURES)),
                         design.T@train.home_margin.to_numpy(float))
    base=base.copy()
    base["baseline_prediction"]=np.column_stack((
        np.ones(len(base)),(base[FEATURES].to_numpy(float)-mu)/sigma))@coef
    matched=network.merge(base[["game_id","baseline_prediction","home_margin"]],
                          on="game_id",validate="one_to_one")
    if not np.all(matched.actual_home_margin==matched.home_margin):
        raise ValueError("Historical game score mismatch")
    def mae(df,w):
        pred=w*df.predicted_home_margin.to_numpy(float)+(
            1-w)*df.baseline_prediction.to_numpy(float)
        return float(np.mean(abs(pred-df.actual_home_margin.to_numpy(float))))
    cal=matched[matched.season==2024]
    test=matched[matched.season==2025]
    if min(len(cal),len(test))<300:
        raise ValueError("Insufficient matched calibration/test games")
    weights=np.linspace(0,1,11)
    # Freeze the 2024 selection BEFORE observing 2025 outcomes.
    weight=float(min(weights,key=lambda w:(mae(cal,w),w)))
    result={
        "status":"RESEARCH_ONLY_NOT_BET",
        "weight_selected_on":"2024",
        "network_weight":weight,
        "calibration_games":len(cal),
        "holdout_year":2025,
        "holdout_games":len(test),
        "baseline_holdout_mae":mae(test,0),
        "network_only_holdout_mae":mae(test,1),
        "blended_holdout_mae":mae(test,weight),
        "limitations":["No sportsbook-price edge validated",
                       "No injury data or calibrated cover probabilities",
                       "No guarantee that improvement persists in 2026"],
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"v6_blend_validation.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)
    return result


if __name__=="__main__":
    compare(Path("data/public_history/pregame_features_2018_2025.csv"),
            Path("data/network_validation/schedule_network_predictions.csv"),
            Path("data/network_validation"))
