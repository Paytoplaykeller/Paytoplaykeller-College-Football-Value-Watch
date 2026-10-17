"""Pregame-only, walk-forward evaluated FBS spread forecast.

No default probabilities. Training requires real, source-attributed historical
features captured BEFORE kickoff. Chronological train/calibration/test prevents
using game results to select the reported probabilities.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import exp, log, sqrt, isfinite
from typing import Sequence
import numpy as np

FEATURES = (
    "home_off_epa", "away_off_epa", "home_def_epa_allowed", "away_def_epa_allowed",
    "home_success_rate", "away_success_rate", "home_havoc_allowed", "away_havoc_allowed",
    "home_havoc_created", "away_havoc_created", "home_explosive_rate", "away_explosive_rate",
    "home_qb_availability", "away_qb_availability", "home_ol_availability", "away_ol_availability",
    "home_def_availability", "away_def_availability", "home_rest_days", "away_rest_days",
    "neutral_site",
)


class ForecastUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class PregameGame:
    game_id: str
    kickoff: datetime
    as_of: datetime
    source: str
    features: dict[str, float]
    # Only historical completed games have a margin.
    final_home_margin: int | None = None
    # Closing market margin is diagnostic only and cannot enter features.
    closing_home_margin: float | None = None


@dataclass(frozen=True)
class CalibratedForecast:
    expected_home_margin: float
    home_margin_probabilities: dict[int, float]
    validation_count: int
    test_count: int
    test_mae: float
    test_spread_brier: float
    test_market_brier: float | None
    test_beats_market: bool | None
    training_cutoff: str
    calibration_cutoff: str
    source: str

    def away_cover_probability(self, away_spread: float) -> float:
        return sum(p for margin,p in self.home_margin_probabilities.items()
                   if -margin + away_spread > 0)

    def home_cover_probability(self, home_spread: float) -> float:
        return sum(p for margin,p in self.home_margin_probabilities.items()
                   if margin + home_spread > 0)


def _check_game(game: PregameGame, *, require_result: bool) -> None:
    if not game.game_id or not game.source:
        raise ForecastUnavailable("Game ID and attributable source required")
    if game.kickoff.tzinfo is None or game.as_of.tzinfo is None or game.as_of >= game.kickoff:
        raise ForecastUnavailable("Timestamped pregame snapshot required")
    if set(game.features) != set(FEATURES):
        raise ForecastUnavailable("Missing or unexpected pregame features")
    if any(not isfinite(float(v)) for v in game.features.values()):
        raise ForecastUnavailable("Nonfinite feature")
    if require_result and (type(game.final_home_margin) is not int):
        raise ForecastUnavailable("Historical final margin missing")


def _matrix(games: Sequence[PregameGame]) -> np.ndarray:
    return np.array([[float(g.features[k]) for k in FEATURES] for g in games], dtype=float)


def _fit(train: Sequence[PregameGame], alpha: float):
    x=_matrix(train)
    y=np.array([g.final_home_margin for g in train],dtype=float)
    mu=x.mean(axis=0)
    sigma=x.std(axis=0)
    sigma[sigma < 1e-9]=1.0
    z=(x-mu)/sigma
    design=np.column_stack((np.ones(len(z)),z))
    penalty=np.diag([0.0]+[alpha]*len(FEATURES))
    try:
        coef=np.linalg.solve(design.T@design+penalty,design.T@y)
    except np.linalg.LinAlgError as exc:
        raise ForecastUnavailable("Singular training design") from exc
    return mu,sigma,coef


def _predict(model, games: Sequence[PregameGame]) -> np.ndarray:
    mu,sigma,coef=model
    z=(_matrix(games)-mu)/sigma
    return np.column_stack((np.ones(len(z)),z))@coef


def _distribution(pred: float, residuals: np.ndarray) -> dict[int,float]:
    # Empirical, discretized held-out residual distribution. Laplace smoothing
    # over nearby outcomes avoids asserting impossible margins.
    if not len(residuals):
        raise ForecastUnavailable("No calibration residuals")
    histogram={}
    for e in residuals:
        center=int(round(pred+float(e)))
        for m,w in ((center-1,0.2),(center,0.6),(center+1,0.2)):
            histogram[m]=histogram.get(m,0.0)+w
    total=sum(histogram.values())
    return {k:v/total for k,v in histogram.items()}


def _home_win_probability(dist: dict[int,float]) -> float:
    return sum(p for margin,p in dist.items() if margin>0)


def _brier(pred: float, actual: bool) -> float:
    return (pred-float(actual))**2


def forecast(
    history: Sequence[PregameGame],
    upcoming: PregameGame,
    *,
    minimum_train: int = 500,
    minimum_calibration: int = 150,
    minimum_test: int = 150,
    alpha: float = 50.0,
) -> CalibratedForecast:
    """Train on earliest 60%, calibrate on next 20%, test on last 20%.

    The final test segment is never used for fitting or calibration. Rejects
    overlapping snapshots and future data. No artificial edge from a point
    estimate or the market line is permitted.
    """
    if alpha<=0:
        raise ForecastUnavailable("Positive regularization required")
    for g in history: _check_game(g,require_result=True)
    _check_game(upcoming,require_result=False)
    ordered=sorted(history,key=lambda g:g.kickoff)
    if len({g.game_id for g in ordered})!=len(ordered):
        raise ForecastUnavailable("Duplicate historical games")
    if any(g.kickoff>=upcoming.as_of for g in ordered):
        raise ForecastUnavailable("History contains games not finished before forecast")
    n=len(ordered)
    a=int(n*0.6)
    b=int(n*0.8)
    train,cal,test=ordered[:a],ordered[a:b],ordered[b:]
    if len(train)<minimum_train or len(cal)<minimum_calibration or len(test)<minimum_test:
        raise ForecastUnavailable("Insufficient independent chronological samples")
    if not (train[-1].kickoff<cal[0].kickoff and cal[-1].kickoff<test[0].kickoff):
        raise ForecastUnavailable("Chronological folds overlap same kickoff time")
    model=_fit(train,alpha)
    residuals=np.array([g.final_home_margin for g in cal])- _predict(model,cal)
    test_predictions=_predict(model,test)
    errors=[]
    bs=[]
    market_bs=[]
    for g,point in zip(test,test_predictions):
        dist=_distribution(float(point),residuals)
        errors.append(abs(float(point)-g.final_home_margin))
        bs.append(_brier(_home_win_probability(dist),g.final_home_margin>0))
        if g.closing_home_margin is not None:
            # A closing spread is a margin estimate, NOT a win probability.
            # Do not compare a transformed spread to calibrated win probability.
            pass
    # A proper market probability baseline requires paired historical moneyline
    # prices; until available, no superiority claim is possible.
    mean_mae=float(np.mean(errors))
    mean_bs=float(np.mean(bs))
    pred=float(_predict(model,[upcoming])[0])
    return CalibratedForecast(
        expected_home_margin=pred,
        home_margin_probabilities=_distribution(pred,residuals),
        validation_count=len(cal),test_count=len(test),
        test_mae=mean_mae,test_spread_brier=mean_bs,
        test_market_brier=None,test_beats_market=None,
        training_cutoff=train[-1].kickoff.isoformat(),
        calibration_cutoff=cal[-1].kickoff.isoformat(),
        source="Chronological ridge model; empirical held-out residual calibration; "+upcoming.source,
    )
