# College-Football-Value-Watch

Stephen Keller's college-football betting research and calibration engine.

## Scope
- Research, market comparison, injury/availability analysis, EV calculations, staking ceilings, futures, ledger tracking, and postgame calibration.
- Advisory only. Stephen manually places, changes, and cashes out wagers.
- Never labels a wager a lock or guarantees profit.

## Core model
- Exact break-even probability from offered odds.
- No-vig market prior when both sides are available.
- Raw fair probability from attributable external models or a clearly labeled model estimate.
- Uncertainty adjustment:

  `p_adj = q_market + lambda * (p_raw - q_market)`

- Normal actionable threshold: 4-5%+ uncertainty-adjusted EV.
- Quarter-Kelly is a ceiling, not a target.
- Model-dispersion, injury, price-quality, and correlation gates can force PASS.

## Protective gates
- Large-Underdog Survival Gate
- Favorite Margin Viability Gate
- Defense Availability Coherence Gate
- Thesis-Consistency Test
- Correlated-Injury Multiplier
- Offensive-Survival Counterbalance Gate

The last gate was added after Kentucky 35, LSU 34 (OT), October 10, 2026, to prevent defensive-injury concerns from automatically overriding a verified multi-path offensive survival thesis.

## Repository layout
- `src/cfb_value_watch/model.py` — probabilities, EV, Kelly, market math
- `src/cfb_value_watch/gates.py` — injury/matchup decision gates
- `src/cfb_value_watch/ledger.py` — confirmed wager ledger schema
- `src/cfb_value_watch/futures.py` — futures valuation helpers
- `config/model_rules.yaml` — tunable thresholds
- `tests/` — regression and calibration tests

## Status
Initial v1 scaffold. Data ingestion and sportsbook adapters are intentionally separated from core logic so external feeds can be swapped without changing model rules.

## Manual-only certified BET evaluation (proposed PR)

The existing BET evaluator can now be called with:
`python -m cfb_value_watch.bet_cli /private/path/verified_evidence.json`

This **local** JSON must contain timestamped, attributed 2026 signals;
independently calibrated p_raw and supported lambda; a matched two-way
no-vig market; verified current injuries, replacements and all protective
gates; a fresh authenticated executable sportsbook quote legally
accessible to the user; and user-confirmed available bankroll/exposure.
The command prints either BET with a manual-only recommendation or NO BET
with blockers. It never places a wager, moves funds, accesses credentials,
or writes a ledger. Never commit private evidence or ticket information
to this public repository or upload it as a workflow artifact.

The separate NFL-Value-Watch public market workflow is research-only.
Historical hit rates alone do not supply an independent calibrated p_raw.
The 2026 suggestions workflow provides LEAN/REVIEW/PASS and does not
promote public market data into an executable offer. Pending merge,
this command is available only from this feature branch.
