# v5 decision engine (proposed, advisory only)

This branch adds `decision_v5.py` and regression tests **without modifying v1 calculations, gates, or the wager ledger**. No betting, account, sportsbook or notification API is called.

## Workflow
1. Research the **full FBS board**, including available props/futures; collect synchronized, attributed market snapshots (opener, consensus, best offered price) and injury reports.
2. Apply position-specific injury and matchup gates already in `gates.py`; document verified independent scoring paths, model dispersion, and any direct injury/thesis conflict.
3. Supply **real** `p_raw`, no-vig `q_market`, lambda, sportsbook price, bankroll and exposure to `Candidate`. Never infer them from final scores or invent unavailable inputs.
4. Run `decide(candidate)`. Critical missing inputs produce WATCH until 90 minutes before kickoff, then PASS. Noncritical uncertainty reduces lambda rather than forcing WATCH.
5. `rank_candidates` puts actionable BET candidates ahead of WATCH candidates, then PASS. Show up to five, but do not manufacture bets to fill a quota.
6. Stephen manually places all wagers. A research recommendation must never create or modify a confirmed wager; only Stephen's confirmation updates the ledger.

## Next integration tasks
- Implement public market/injury/prop feed adapters with source timestamps and freshness checks.
- Calculate source-backed independent forecast probabilities, including home-underdog and offensive-survival factors; validate with historical *pregame* forecasts.
- Integrate the hourly scheduler and final 24h/6h/90m decision checkpoints.
- Compare v5 and existing decisions over historical and prospective games, with calibration and CLV as diagnostics only.
- Add explicit correlation limits, actual bankroll-based staking, and sportsbook line/price invalidation conditions before live recommendation deployment.

This branch does **not** claim that a data feed, hourly runner, calibrated predictive model, or production deployment already exists.
