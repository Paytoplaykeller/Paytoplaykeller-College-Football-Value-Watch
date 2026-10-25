# Historical favorite-overpricing / underdog test

Research implementation: `src/cfb_value_watch/market_backtest.py`.

Sources: SportsDataverse frozen weekly schedule-network projections and
ESPN CFB betting release for 2024 and 2025. The betting release has
`home_team_spread` and `odds_source`; rows from `default` and
`injected` are excluded. Conflicting lines for a game are excluded.

1. Determine the market favorite from the sign of home spread.
2. Compute market-implied favorite winning margin = absolute home spread.
3. Compute the model's projected favorite margin using its frozen weekly
   forecast; `gap = market favorite margin - model favorite margin`.
4. On 2024, evaluate thresholds 0, 2, 3, 5, 7, 10 points, selecting the
   highest hypothetical flat-stake ROI with at least 35 selections.
5. Freeze that threshold; evaluate it on 2025 unseen games, including failed
   underdog covers. Report wins/losses/pushes, a Wilson lower bound, and
   hypothetical -110 ROI. Also compare model and market margin MAE on the
   exact same games.

**Critical limitations:** Historical ESPN release lines have no guaranteed
quote timestamp or actual executable American odds. A retrospective line
may reflect late information, so it cannot establish a true as-of betting
strategy. The -110 calculation is only a hypothetical sensitivity
analysis. This test excludes injuries, offense viability and live book
availability. It is NOT a positive-EV or BET authorization. Do not change
the model or staking based on three winning examples.

The next phase requires point-in-time paired bookmaker odds and archived
personnel availability. The same holdout framework can then evaluate
favorite-margin fragility and offensive survival conditional on genuine
pregame evidence, and compare results with market probabilities and actual
book prices.
