from datetime import datetime,timedelta,timezone
import pytest
from cfb_value_watch.underdog_mispricing import MispricingEvidence,screen
T=datetime(2026,10,17,22,tzinfo=timezone.utc)

def fixture(**kw):
    data=dict(event_id="frozen",as_of=T,kickoff=T+timedelta(hours=2),
              public_quote_at=T-timedelta(minutes=5),
              market_favorite_margin=10.5,network_favorite_margin=6.0,
              network_home_games_seen=6,network_away_games_seen=6,
              independent_model_agreement=True,
              favorite_drive_sustainability=False,favorite_margin_paths=1,
              underdog_offensive_floor=True,underdog_cover_paths=2,
              qb_ol_availability_verified=True,source="archived pregame quotes")
    data.update(kw)
    return MispricingEvidence(**data)

def test_priority_screen_never_authorizes_bet():
    result=screen(fixture())
    assert result["status"]=="PRIORITY_UNDERDOG_RESEARCH"
    assert result["bet_authorized"] is False
    assert result["p_raw_delta"]==0

def test_weak_underdog_offense_is_not_a_signal():
    assert screen(fixture(underdog_offensive_floor=False))["status"]=="NO_SIGNAL"

def test_missing_injuries_blocks():
    assert screen(fixture(qb_ol_availability_verified=False))["status"]=="INCOMPLETE_PREGAME_EVIDENCE"

def test_no_discrepancy_no_signal():
    assert screen(fixture(network_favorite_margin=9.5))["status"]=="NO_SIGNAL"

def test_post_kickoff_quote_rejected():
    with pytest.raises(ValueError):
        screen(fixture(public_quote_at=T+timedelta(hours=3)))

def test_no_synthetic_conference_bonus():
    assert "conference" not in fixture().__dict__
