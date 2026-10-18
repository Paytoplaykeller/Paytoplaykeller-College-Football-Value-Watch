# Dynamic Strength of Schedule v6 — implemented research module

## What it computes

`schedule_network.py` fits a regularized schedule graph to final scoring
margins from completed games available **before** the forecast timestamp.

For a home-vs-away matchup:

`predicted margin = home-team effect - away-team effect
+ home-conference effect - away-conference effect + venue effect`

The team effects are penalized (shrunken toward zero), and conference effects
are penalized more heavily. Conference membership is taken from the season of
each actual game. There is **no hand-assigned SEC bonus** and no reward for a
team's name, AP rank, or win-loss record.

Opponents connect teams: Kentucky's result against LSU and LSU's results against
other schools inform Kentucky's rating indirectly. Quality of victories and
losses are accounted for through the opponent graph rather than a manual
ranked-win score.

The fit caps each observed scoring margin at 35 to reduce the influence of
garbage-time blowouts, discounts older games, and learns home advantage.
The output also reports conference contributions separately so they can be
audited. Conference strength is uncertain with limited cross-conference games.

## Historical validation

`python -m cfb_value_watch.network_backtest --out data/network_validation`

The pipeline downloads 2021–2025 public FBS schedule files, freezes ratings at
the beginning of each UTC calendar week, and predicts only later games.
It reports 2024 validation and 2025 holdout margin MAE/RMSE/bias and exports
per-game predictions. It does not tune parameters using the 2025 holdout.

## Critical limitations

- This is a margin model, **not** a calibrated cover probability or positive-EV model.
- No historical paired sportsbook prices, no injury availability and no play-by-play
  offensive/defensive adjustment are yet included.
- Earlier games from the same week are deliberately excluded, sacrificing some
  recency to prevent accidental leakage.
- Cross-conference effect estimates can be unstable. Require a minimum
  cross-conference sample and bootstrap uncertainty before trusting them.
- A single upset, including Kentucky–Oklahoma, does not validate the model.
- This module must not automatically elevate WATCH to BET or alter bankroll
  controls until independently validated and integrated with the decision engine.

Source: SportsDataverse `cfb_schedules` season Parquet release, with
home/away conference and game outcome fields.
