"""Independent historical underdog-price-dislocation test, 2024/2025.

Sources:
 - SportsDataverse ESPN CFB betting (retrospective spread records)
 - Frozen weekly opponent-network predictions from network_backtest.py

CAVEAT: ESPN betting release does not guarantee a timestamped executable quote
or American odds. All ROI is hypothetical -110, never an actual bet result.
2024 selects one threshold; 2025 is untouched evaluation.
"""
from __future__ import annotations
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd

BETTING_URL = ("https://github.com/sportsdataverse/sportsdataverse-data/"
               "releases/download/espn_cfb_betting/betting_{year}.parquet")
ALLOWED_SOURCES = {"summary_pickcenter", "core_odds_api"}
THRESHOLDS = (0.0, 2.0, 3.0, 5.0, 7.0, 10.0)
MIN_CAL_SELECTIONS = 35


def wilson_lower(wins: int, n: int, z: float = 1.96) -> float | None:
    if n == 0:
        return None
    p = wins/n
    return ((p + z*z/(2*n) -
             z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1+z*z/n))


def load_betting(years=(2024, 2025)):
    frames = []
    for year in years:
        df = pd.read_parquet(BETTING_URL.format(year=year))
        required = {"game_id", "home_team_spread", "odds_source",
                    "game_spread_available"}
        missing = required-set(df.columns)
        if missing:
            raise ValueError(f"{year} betting release missing {sorted(missing)}")
        df = df.copy()
        df["source_year"] = year
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def join_market(network: pd.DataFrame, betting: pd.DataFrame) -> tuple[pd.DataFrame,dict]:
    net = network.copy()
    net["game_id"] = net.game_id.astype(str)
    net = net[net.season.isin([2024,2025])]
    if net.game_id.duplicated().any():
        raise ValueError("Duplicate frozen model predictions")
    market = betting.copy()
    market["game_id"] = market.game_id.astype(str)
    raw = len(market)
    market["home_team_spread"] = pd.to_numeric(market.home_team_spread,errors="coerce")
    market = market[
        market.odds_source.isin(ALLOWED_SOURCES) &
        (market.game_spread_available == True) &
        market.home_team_spread.notna() &
        market.home_team_spread.between(-60,60)
    ].copy()
    # A game may have multiple providers/records. Require exact consensus
    # across all retained records; otherwise exclude rather than cherry-pick.
    conflicts = market.groupby("game_id").home_team_spread.nunique()
    conflicting_ids = set(conflicts[conflicts>1].index)
    market = market[~market.game_id.isin(conflicting_ids)]
    market = market.sort_values(["game_id","odds_source"]).drop_duplicates("game_id")
    joined = net.merge(market[["game_id","home_team_spread","odds_source"]],
                       on="game_id",how="inner",validate="one_to_one")
    if not joined.empty:
        joined["favorite_margin_market"] = joined.home_team_spread.abs()
        joined["home_favorite"] = joined.home_team_spread < 0
        # Positive = bookmaker's favorite is more favored than the model says.
        joined["model_favorite_margin"] = np.where(
            joined.home_favorite,joined.predicted_home_margin,
            -joined.predicted_home_margin)
        joined["favorite_overpricing"] = (
            joined.favorite_margin_market - joined.model_favorite_margin)
        # Selected side always the market underdog, excluding pick'ems.
        joined["underdog_actual_margin"] = np.where(
            joined.home_favorite,-joined.actual_home_margin,
            joined.actual_home_margin)
        joined["underdog_points"] = joined.favorite_margin_market
        joined["ats_margin"] = joined.underdog_actual_margin + joined.underdog_points
        joined["ats_result"] = np.where(joined.ats_margin>1e-8,"WIN",
                                np.where(joined.ats_margin < -1e-8,"LOSS","PUSH"))
    coverage = {"raw_betting_rows":raw,
                "valid_nondefault_rows":len(market),
                "conflicting_games_excluded":len(conflicting_ids),
                "frozen_network_rows":len(net),
                "matched_rows":len(joined)}
    return joined,coverage


def measure(df: pd.DataFrame, threshold: float) -> dict:
    if df.empty:
        return {"n":0,"wins":0,"losses":0,"pushes":0,
                "win_rate_decided":None,"roi_at_hypothetical_minus110":None,
                "wilson_lower_win_rate":None}
    picked = df[(df.favorite_margin_market>0)&
                (df.favorite_overpricing>=threshold)]
    wins=int((picked.ats_result=="WIN").sum())
    losses=int((picked.ats_result=="LOSS").sum())
    pushes=int((picked.ats_result=="PUSH").sum())
    n=wins+losses
    return {"n":len(picked),"wins":wins,"losses":losses,"pushes":pushes,
            "win_rate_decided":wins/n if n else None,
            "roi_at_hypothetical_minus110":(wins*(100/110)-losses)/len(picked)
                if len(picked) else None,
            "wilson_lower_win_rate":wilson_lower(wins,n)}


def evaluate(network_csv: Path, betting: pd.DataFrame, output: Path) -> dict:
    network=pd.read_csv(network_csv)
    joined,coverage=join_market(network,betting)
    cal=joined[joined.season==2024]
    test=joined[joined.season==2025]
    if min(len(cal),len(test))<150:
        raise ValueError(f"Insufficient comparable historical markets: "
                         f"2024={len(cal)}, 2025={len(test)}")
    grid={str(t):measure(cal,t) for t in THRESHOLDS}
    # Pick best 2024 hypothetical ROI among thresholds with adequate sample.
    # Ties prefer lower threshold. Selection bias remains, so 2025 is held out.
    eligible=[t for t in THRESHOLDS
              if grid[str(t)]["n"]>=MIN_CAL_SELECTIONS]
    if not eligible:
        raise ValueError("No 2024 threshold has sufficient sample")
    selected=max(eligible,key=lambda t:(grid[str(t)]["roi_at_hypothetical_minus110"],-t))
    holdout=measure(test,selected)
    all_dogs=measure(test,0.0)
    # Market implied favorite margin is -home spread; compare point forecasts
    # on the identical games, never conflate this with odds or EV.
    margin_market=-test.home_team_spread.to_numpy(float)
    margin_model=test.predicted_home_margin.to_numpy(float)
    actual=test.actual_home_margin.to_numpy(float)
    report={
        "status":"RESEARCH_ONLY_NOT_BET",
        "source":"SportsDataverse ESPN CFB betting + frozen weekly opponent-network",
        "line_provenance_allowed":sorted(ALLOWED_SOURCES),
        "coverage":coverage,
        "2024_threshold_selection":grid,
        "selected_discrepancy_threshold":selected,
        "2025_holdout":holdout,
        "2025_all_discrepant_underdogs":all_dogs,
        "2025_matched_games":len(test),
        "2025_market_margin_mae":float(np.mean(np.abs(margin_market-actual))),
        "2025_network_margin_mae":float(np.mean(np.abs(margin_model-actual))),
        "hypothetical_break_even_minus110":110/210,
        "positive_ev_verified":False,
        "limitations":[
            "Historical lines lack verified pregame quote timestamps and executable odds",
            "Hypothetical -110 ROI is not realized or verifiable sportsbook ROI",
            "No archived QB/OL/injury or favorite fragility flags in this dataset",
            "Threshold search on 2024 requires independent 2025 evaluation",
            "One season of holdout is insufficient for deployment",
            "No bankroll changes, BET authorization or wagering transactions",
        ],
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"market_dislocation_holdout.json").write_text(json.dumps(report,indent=2))
    joined.to_csv(output/"matched_market_network.csv",index=False)
    print(json.dumps(report,indent=2),flush=True)
    return report


if __name__=="__main__":
    evaluate(Path("data/network_validation/schedule_network_predictions.csv"),
             load_betting(),Path("data/market_audit"))
