from dataclasses import asdict
from datetime import datetime, timezone

from cfb_value_watch.cli import inspect


def test_empty_evidence_fails_closed():
    out = inspect({})
    assert out["status"] == "NO_BET"


def test_fake_approved_flags_cannot_certify():
    now = "2026-10-25T12:00:00+00:00"
    data = dict(
        selection="fictional", market="spreads", odds=-110, line=-3.5,
        event_id="fictional", source_revision="synthetic",
        model_run_id="synthetic", quote_timestamp=now, evaluated_at=now,
        executable_quote_verified=True, sportsbook="fake",
        q_market=.5, p_raw=.75, lam=.8, model_dispersion_points=1.,
        independent_forecast_verified=True, no_vig_same_market_verified=True,
        availability_verified=True, replacements_verified=True,
        thesis_verified=True, opponent_strength_verified=True,
        venue_weather_verified=True,
        gate_results={k:True for k in ("defense_availability","favorite_margin",
            "large_underdog","offensive_survival","correlated_injury","thesis_consistency")},
        available_bankroll=1000, total_correlated_exposure=0, proposed_stake=20,
    )
    out=inspect(data)
    assert out["status"] == "NO_BET"
    assert "not authenticated" in out["blockers"][-1]


def test_unknown_fields_fails_closed():
    assert inspect({"secret_key": "never"})["status"] == "NO_BET"


def test_bad_timestamp_fails_closed():
    assert inspect({"quote_timestamp": "not-a-date"})["status"] == "NO_BET"
