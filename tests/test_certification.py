from dataclasses import replace
from datetime import datetime, timedelta, timezone

from cfb_value_watch.certification import CertificationEvidence, certify_bet

NOW = datetime(2026, 10, 24, 16, 0, tzinfo=timezone.utc)
GATES = {name: True for name in (
    "defense_availability", "favorite_margin", "large_underdog",
    "offensive_survival", "correlated_injury", "thesis_consistency"
)}


def valid_evidence():
    return CertificationEvidence(
        selection="Example", market="spreads", odds=-110, line=-3.5,
        event_id="test-only", source_revision="fake-fixture-sha",
        model_run_id="fixture-only", quote_timestamp=NOW - timedelta(seconds=10),
        evaluated_at=NOW, executable_quote_verified=True, sportsbook="test-fixture",
        q_market=0.5, p_raw=0.75, lam=0.8, model_dispersion_points=1.0,
        independent_forecast_verified=True, no_vig_same_market_verified=True,
        availability_verified=True, replacements_verified=True,
        thesis_verified=True, opponent_strength_verified=True,
        venue_weather_verified=True, gate_results=GATES,
        available_bankroll=1000, total_correlated_exposure=0, proposed_stake=20,
    )


def test_complete_synthetic_evidence_passes_math_only():
    # Synthetic proof of function behavior, never an executable real-world bet.
    r = certify_bet(valid_evidence())
    assert r.status == "BET"
    assert r.ev > 0.04


def test_missing_own_model_blocks():
    r = certify_bet(replace(valid_evidence(), p_raw=None,
                            independent_forecast_verified=False))
    assert r.status == "NO_BET"


def test_public_quote_is_not_executable():
    r = certify_bet(replace(valid_evidence(), executable_quote_verified=False))
    assert r.status == "NO_BET"


def test_stale_quote_rejected():
    r = certify_bet(replace(valid_evidence(),
                            quote_timestamp=NOW - timedelta(minutes=5)))
    assert r.status == "NO_BET"


def test_favorite_margin_gate_blocks_even_good_ev():
    bad = dict(GATES, favorite_margin=False)
    assert certify_bet(replace(valid_evidence(), gate_results=bad)).status == "NO_BET"


def test_uncertified_replacements_block():
    assert certify_bet(replace(valid_evidence(), replacements_verified=False)).status == "NO_BET"


def test_missing_bankroll_blocks():
    assert certify_bet(replace(valid_evidence(), available_bankroll=None)).status == "NO_BET"


def test_kelly_cap_blocks_oversized_stake():
    assert certify_bet(replace(valid_evidence(), proposed_stake=500)).status == "NO_BET"


def test_false_qualitative_evidence_blocks():
    assert certify_bet(replace(valid_evidence(), thesis_verified=False)).status == "NO_BET"


def test_missing_any_gate_blocks():
    assert certify_bet(replace(valid_evidence(), gate_results={})).status == "NO_BET"


def test_different_market_line_cannot_use_unverified_prior():
    assert certify_bet(replace(valid_evidence(), no_vig_same_market_verified=False)).status == "NO_BET"
