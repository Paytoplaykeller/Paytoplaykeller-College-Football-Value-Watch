# Shadow totals calibration protocol — October 22, 2026

This research module is isolated from the existing spread forecasting, pricing, gates, and ledger. No existing code or model thresholds were modified.

## Inputs required before any fitted totals model
- Independent, timestamped pre-kickoff **total probability** forecasts. A point-spread distribution is not a totals probability.
- An unbiased chronological sample of games, including losing predictions, no-bet games and different scoring environments.
- Exact settled total lines and final results, plus historical two-sided prices for testing value against bookmaker baselines.
- Team points, pace, offensive efficiency, explosive-play rates, defense and special-teams exposures measured before kickoff; do not replace missing values with postgame observations.
- Correlated positions grouped by game with joint outcomes. Treat full-game Under and team-total Under as a portfolio-level cluster, not independent risk.

## Initial procedure
1. Freeze original baseline forecasts, probabilities, odds and timestamps.
2. Partition by kickoff date into chronological train/calibration/holdout sets before exploring candidates.
3. Run `totals_shadow.reliability_report` on original held-out probabilities and outcomes. It provides Brier, log loss and calibration bins only.
4. Require sufficient independent examples in each relevant market and compare against no-vig market baseline. The 200-game diagnostic floor is NOT evidence of model performance or approval.
5. Develop alternative totals prediction/calibration only after genuine pregame sources are available, compare on completely unseen games, then assess uncertainty, nonoffensive scoring, variance, and joint-loss frequencies.
6. Keep baseline intact and review proposed changes separately. No resulting code automatically recommends betting.

## New Mexico State–Sam Houston case
Final 30–24. Full-game Under 46.5 and Sam Houston team Under 21.5 lost; New Mexico State -2.5 bonus won. This case is a **diagnostic example**, not fitting or tuning data for a single-game special-teams penalty. The previous Under recommendation was qualitative and not a traceable approved model output.

## Known blockers
No source-attributed, point-in-time full-game/team-total probability archive is available in this repo. Therefore no fitted totals calibration, empirical joint-loss estimate, or BET approval is claimed.
