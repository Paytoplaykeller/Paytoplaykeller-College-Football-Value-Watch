from datetime import datetime, timedelta, timezone
from dataclasses import replace

from cfb_value_watch.certification import CertificationInput, certify_bet

NOW = datetime(2026, 10, 26, 20, tzinfo=timezone.utc)


def example():
    return CertificationInput(
        selection="Sample +3.5", offered_american_odds=-110,
        opposite_american_odds=-110, public_quote_at=NOW,
        executable_hard_rock_verified=True, executable_quote_at=NOW,
        sportsbook_authorized_in_location=True,
        forecast_source="validated internal model release",
        calibrated_independent_forecast=True, p_raw=.64,
        lambda_justification="documented holdout-calibrated uncertainty", lam=.80,
        model_dispersion_points=1.0, availability_verified=True,
        all_protective_gates_passed=True, verified_bankroll=1000.,
        proposed_stake=10.,
    )


def test_mathematically_valid_complete_evidence_can_certify():
    assert certify_bet(example(), now=NOW).decision == "BET"


def test_no_forecast_never_certifies():
    x = replace(example(), p_raw=None, calibrated_independent_forecast=False)
    assert certify_bet(x, now=NOW).decision == "NO BET"


def test_public_odds_are_not_executable_quotes():
    x = replace(example(), executable_hard_rock_verified=False)
    assert certify_bet(x, now=NOW).decision == "NO BET"


def test_missing_same_market_opposite_price_blocks():
    assert certify_bet(replace(example(), opposite_american_odds=None), now=NOW).decision == "NO BET"


def test_stale_quote_blocks():
    x = replace(example(), executable_quote_at=NOW - timedelta(hours=1))
    assert certify_bet(x, now=NOW).decision == "NO BET"


def test_unverified_injury_blocks():
    assert certify_bet(replace(example(), availability_verified=False), now=NOW).decision == "NO BET"


def test_failed_protective_gate_blocks():
    assert certify_bet(replace(example(), all_protective_gates_passed=False), now=NOW).decision == "NO BET"


def test_unknown_bankroll_blocks():
    assert certify_bet(replace(example(), verified_bankroll=None), now=NOW).decision == "NO BET"


def test_oversized_stake_blocks():
    assert certify_bet(replace(example(), proposed_stake=900), now=NOW).decision == "NO BET"


def test_no_bet_below_threshold():
    assert certify_bet(replace(example(), p_raw=.50), now=NOW).decision == "NO BET"
