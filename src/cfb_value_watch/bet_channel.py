"""Manual-only BET channel. A qualitative LEAN never becomes BET without verified inputs."""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from .lean_2026 import LeanCandidate, assess_lean
from .model import no_vig_two_way, adjusted_probability, expected_value_per_unit, quarter_kelly_fraction

GATES = ("defense_availability", "favorite_margin", "large_underdog",
         "offensive_survival", "correlated_injury", "thesis_consistency")

@dataclass(frozen=True)
class BetEvidence:
    lean: LeanCandidate
    book: str
    line: float
    odds: int
    opposite_odds: int
    same_market_verified: bool
    quote_at: datetime
    executable_quote_verified: bool
    local_access_verified: bool
    forecast_source: str
    independent_2026_forecast_verified: bool
    p_raw: float | None
    lam: float | None
    lambda_rationale: str
    dispersion: float | None
    critical_availability_verified: bool
    matchup_verified: bool
    gates: dict[str, bool]
    available_bankroll: float | None
    existing_exposure: float | None
    proposed_stake: float | None

@dataclass(frozen=True)
class BetDecision:
    status: str
    reasons: tuple[str, ...]
    instruction: str = ""
    p_adj: float | None = None
    ev: float | None = None

def evaluate(e: BetEvidence, *, min_ev=.04, max_quote_age=120) -> BetDecision:
    reasons=[]
    def require(ok, why):
        if not ok: reasons.append(why)
    require(assess_lean(e.lean).status=="LEAN", "2026 lean not qualified")
    require(bool(e.book) and e.executable_quote_verified and e.local_access_verified,
            "authenticated executable accessible price missing")
    require(e.same_market_verified, "same-market paired quote not verified")
    require(bool(e.forecast_source) and e.independent_2026_forecast_verified,
            "independently calibrated 2026 forecast missing")
    require(bool(e.lambda_rationale), "lambda rationale missing")
    require(e.critical_availability_verified and e.matchup_verified,
            "personnel, replacements or matchup evidence incomplete")
    for gate in GATES: require(e.gates.get(gate) is True, f"gate missing/failed: {gate}")
    require(e.quote_at.tzinfo is not None and 0 <= (e.lean.evaluated_at-e.quote_at).total_seconds() <= max_quote_age,
            "executable quote not fresh")
    for val,name,lo,hi in ((e.p_raw,"p_raw",0,1),(e.lam,"lambda",0,1),(e.dispersion,"dispersion",0,4.5)):
        require(type(val) in (int,float) and isfinite(val) and lo<=val<=hi,"invalid "+name)
    for val,name in ((e.available_bankroll,"bankroll"),(e.existing_exposure,"exposure"),(e.proposed_stake,"stake")):
        require(type(val) in (int,float) and isfinite(val) and val>=0,"invalid "+name)
    if reasons: return BetDecision("NO BET",tuple(reasons))
    if e.available_bankroll<=0 or e.proposed_stake<=0:
        return BetDecision("NO BET",("no authorized available stake",))
    try:
        q,_=no_vig_two_way(e.odds,e.opposite_odds)
        p=adjusted_probability(q,e.p_raw,e.lam)
        ev=expected_value_per_unit(p,e.odds)
        cap=min(40.0,e.available_bankroll-e.existing_exposure,
                e.available_bankroll*quarter_kelly_fraction(p,e.odds))
    except (ValueError,ZeroDivisionError):
        return BetDecision("NO BET",("odds calculation failed",))
    if ev<min_ev or e.proposed_stake>cap or cap<=0:
        return BetDecision("NO BET",("EV/quarter-Kelly/exposure threshold failed",),p_adj=p,ev=ev)
    instruction=(f"Manual only: {e.lean.selection} at {e.book}, {e.odds:+d}; "
                 f"maximum proposed stake ${e.proposed_stake:.2f}. "
                 "Recheck line, odds, and availability before placement. No wager placed.")
    return BetDecision("BET",(),instruction,p,ev)
