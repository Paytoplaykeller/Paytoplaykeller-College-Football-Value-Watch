# October 17, 2026: frozen three-underdog diagnostic

**Research only. Not a retrospectively approved BET.**

The SportsDataverse opponent-network replay used a frozen 2026-10-17
18:00 Eastern snapshot, before all three kickoffs. GitHub Actions run:
https://github.com/Paytoplaykeller/Paytoplaykeller-College-Football-Value-Watch/actions/runs/39095943990

| Underdog | Archived public market favorite | Frozen network favorite margin | Favorite overpricing hypothesis (market - network) |
|---|---:|---:|---:|
| Kentucky at Oklahoma | Oklahoma 6.5 | Oklahoma 7.585 | -1.085 |
| BYU hosting Notre Dame | Notre Dame 10.5 | Notre Dame 1.309 | +9.191 |
| Florida State at Miami | Miami 21.5 | Miami 15.094 | +6.406 |

Archived public lines: CBS 2026 week 7 odds board
https://www.cbssports.com/college-football/odds/top25/2026/regular/week-7/

These comparisons are **point-estimate differences**, not calibrated cover
probabilities or positive EV. The public prices were not integrated into the
GitHub replay itself and are not verified Hard Rock execution quotes.

## Findings

- BYU and Florida State displayed large pregame public-market vs schedule-network
  discrepancies. The candidate signal is market favorite margin overpricing,
  especially if favorite margin creation is fragile and underdog offense survives.
- Kentucky did NOT show this discrepancy: the network projected Oklahoma by 7.6
  versus market 6.5. Kentucky requires a separate evidence channel (offensive
  sustainability, opponent-adjusted scoring, QB/OL availability, favorite margin
  fragility, and non-offensive-score dependence).
- A common pattern cannot be declared from three selected successful underdogs.
  Include all large underdogs, including failed covers, when validating.
- For any candidate, verify pregame odds, injuries, independent projections,
  no-vig market probability, exact-line calibrated cover probability, and EV.
  The engine must return WATCH/PASS when these are unavailable.

## Next historical experiment (not yet run)

Join frozen weekly network projections to contemporaneous, paired sportsbook
spread prices for every 2024–2026 FBS game. Bucket by market-minus-model
discrepancy, favorite scoring sustainability, dog offensive floor, spread size,
home/away and conference strength. Compare against 2024 development and 2025
holdout without changing weights based on October 17 outcomes. Evaluate
profitability after vig, uncertainty and correlated exposures. This will test
whether the apparent favorite-overpricing effect is genuine.
