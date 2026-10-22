# Conference strength and postseason validation

The v6 opponent-network already estimates team and conference effects jointly.
Do not add the conference effect again as an independent bonus.

The cross-conference holdout audit:
- Reads frozen weekly 2024 and 2025 forecasts.
- Compares prediction residuals in games between conferences.
- Separates each season and conference pairing.
- Suppresses mean residual estimates with fewer than 25 games.
- Does not infer that a conference or bowl team is guaranteed to win.

To run: `python -m cfb_value_watch.conference_audit_cli` after
`python -m cfb_value_watch.network_backtest`.

Bowl and CFP forecasts must also verify QB/OL status, opt-outs and transfers,
coaching changes, defensive availability and special teams before the
decision engine may approve a BET. Missing verification is not a positive signal.

For a true betting edge, compare against time-stamped paired sportsbook prices,
calibrated cover probabilities, and actual pregame rosters. Evaluate bowl and
non-bowl games separately on multiple historical seasons. Bowl opt-out data
are not present in the public schedule dataset; do not backfill them using
postgame information. Avoid choosing conference weights based on outcomes
of a few high-profile bowls.

The conference audit is diagnostic, not a production probability or EV model.
