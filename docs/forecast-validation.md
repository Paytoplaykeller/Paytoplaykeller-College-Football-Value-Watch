# v5 forecast: historical validation contract

The new `forecast_v5.py` and `forecast_cli.py` do **not** claim to have trained a predictive model on real FBS history. They reject missing data and return research-only probabilities until externally verified.

## Required historical input
Use one unique game per row, with UTC-aware kickoff and pregame snapshot `as_of` timestamps, attributable `source`, final home scoring margin (training target only), and all features listed in `FEATURES` of `forecast_v5.py`. Every feature must reflect what was known at `as_of`, never postgame information. No future rankings, closing odds, results, or retrospective injury knowledge in features. Normalize offensive/defensive measures to the same season/opponent-adjusted methodology. Availability features must use a documented numeric coding scheme consistently across historical and upcoming games.

## Evaluation
- Chronological 60% train / 20% calibration / 20% untouched test. Default minimum 500 train, 150 calibration and 150 test games.
- Ridge-regularized margin projection; empirical calibration-residual distribution, with discrete one-point smoothing, for exact cover probabilities.
- Report test MAE and home-win Brier. A proper comparison to the market requires timestamped **pregame two-sided prices**, which are not yet provided; `test_beats_market` is explicitly null.
- Test multiple seasons and walk-forward windows before deployment; monitor reliability by line bucket, favorites/underdogs, venue and injury severity.
- The current 60/20/20 evaluation is a starting benchmark, **not** evidence of calibration or superiority. Check drift and replace with rolling walk-forward validation before live approval.
- Closing lines are diagnostic only. Do not optimize model parameters against test outcomes or use CLV as proof of positive EV.

## Integration gate
No `BET` authorization until the historical data have been verified, the holdout forecast is demonstrably calibrated and useful against a proper no-vig market baseline, the exact market contract is paired, current critical availability is checked, and the accepted Hard Rock price is verified. A research forecast alone is not permission to bet. Preserve manual-only transactions and existing ledgers.

Run with:
```
python -m cfb_value_watch.forecast_cli --history pregame_history.csv --upcoming target.json
```
