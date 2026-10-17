from datetime import datetime,timedelta,timezone
import pytest
from cfb_value_watch.underdog_regime import (
    UnderdogSample,audit_underdog_trend,same_day_dog_signal
)

NOW=datetime(2026,10,17,22,tzinfo=timezone.utc)

def sample(i,cover=True):
    kickoff=NOW-timedelta(days=365+i)
    return UnderdogSample(
        game_id=f"g{i}",kickoff=kickoff,snapshot_at=kickoff-timedelta(hours=4),
        spread=7.5,cover=cover,no_vig_cover_probability=.5,
        source="archived two-sided bookmaker snapshot",home=True)

def test_same_day_hot_dogs_do_not_change_probability_or_stake():
    signal=same_day_dog_signal(4,4)
    assert signal["status"]=="DESCRIPTIVE_ONLY"
    assert signal["p_raw_delta"]==0
    assert signal["lambda_multiplier"]==1
    assert signal["stake_multiplier"]==1

def test_small_sample_does_not_create_edge():
    audit=audit_underdog_trend([sample(i) for i in range(8)],evaluation_before=NOW)
    assert audit.status=="INSUFFICIENT_EVIDENCE"
    assert audit.adjustment_allowed is False

def test_even_large_historical_signal_needs_holdout():
    records=[sample(i) for i in range(250)]
    audit=audit_underdog_trend(records,evaluation_before=NOW)
    assert audit.status=="HYPOTHESIS_REQUIRES_INDEPENDENT_HOLDOUT"
    assert audit.adjustment_allowed is False

def test_non_pregame_quotes_are_rejected():
    s=sample(1)
    bad=UnderdogSample(s.game_id,s.kickoff,s.kickoff,s.spread,
                       s.cover,s.no_vig_cover_probability,s.source,s.home)
    with pytest.raises(ValueError):
        audit_underdog_trend([bad],evaluation_before=NOW)

def test_duplicate_games_do_not_inflate_edge():
    with pytest.raises(ValueError):
        audit_underdog_trend([sample(1),sample(1)],evaluation_before=NOW)
