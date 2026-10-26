# BET NOW evidence contract (draft; not a live sportsbook adapter)

The existing handicapping model, 4% adjusted-EV threshold, 4.5-point
dispersion limit, protective matchup gates, quarter-Kelly cap, bankroll
controls and ledger are unchanged.

## Run

From the repository root, with the package installed, run:

```sh
python -m cfb_value_watch.decision_cli evidence.json
```

The JSON must contain **real** timestamped evidence; never copy the
synthetic fixtures in `tests/` into production.

## Input requirements

- `offered_odds`, `opposite_odds`: integers for the SAME two-sided
  spread/total/moneyline market; include both `source` and
  `opposite_source`, `no_vig_same_market: true`.
- `quote_time`: timezone-aware ISO datetime no more than 15 minutes old.
  `executable: true` may only be set after a user-confirmed Hard Rock
  quote or authenticated live account source; a scraped aggregator quote
  is **not** an executable price.
- `forecast_source`, `forecast_timestamp`, `p_raw`,
  `forecast_uses_market_implied_probability: false`: the attributable
  current output of Stephen's own opponent-adjusted forecast, not a
  media lean or third-party consensus. `lambda` must include injury and
  uncertainty discounts. `dispersion_points` must come from the same
  calibrated forecast ensemble or approved model process.
- `availability`: a dictionary covering all ten role categories listed
  in `decision_engine.REQUIRED_ROLES`. Each item specifies
  `material: true/false`. Material positions require
  `checked: true`, `source`, and timezone-aware `checked_at`
  within 24 hours. Immaterial unchecked positions additionally require
  `uncertainty_accounted_for: true`, a reason, and top-level
  `minor_uncertainty_lambda_applied: true`. No automatic or arbitrary
  haircut is assigned by the engine.
- `gates`: all six protective gates must have explicit `applicable`
  and `reason`; applicable gates require `passed: true`.
  Nonapplicable gates require `applicability_evidence`. Do not mark a
  problematic gate nonapplicable to force approval.
- `price_limit_verified`, `opposing_case_checked`,
  `invalidation_checked` must be true only when documented.
- `available_bankroll`, `bankroll_stake_cap`, `stake_grade` must
  reflect actual authorized bankroll policy, not sample fixtures.

A qualifying record returns `BET` with break-even, no-vig market
prior, adjusted probability, EV, quarter-Kelly and **maximum** stake.
Otherwise the CLI returns `PASS` with explicit blockers and zero stake.
No wagers or funds transfers are performed.

## Production limitations and milestones

1. **Own-model forecast adapter**: export current model predictions,
   feature versions, data cutoff, calibration and dispersion. This is
   not implemented in this PR; historical unit-test success is not a
   fresh game forecast.
2. **Odds adapter**: authenticate quotes where permitted, or accept a
   user-confirmed timestamped Hard Rock line. This is not implemented.
3. **Material availability assessor**: tag each unit using projected
   snaps, role, replacements and matchup importance; record primary
   sources. This is not yet an automatic injury feed.
4. **Historical replay**: reconstruct selections and lines strictly as
   known at prediction time, including losing selections, and compare
   old versus materiality-aware gates. Verify the claimed 81.6% record
   against its actual sample; do not assume it generalizes.
5. **CI and shadow run**: execute all tests and full-board audit before
   enabling production BET labels. Keep this draft PR unmerged until
   reviewed.

External forecaster disagreements are NOT a betting gate. The
authoritative open-position ledger remains unchanged and private.
