from datetime import datetime,timedelta,timezone
import pytest
from cfb_value_watch.favorite_fragility import FavoriteFragilityEvidence,favorite_fragility_gate

T=datetime(2026,10,17,23,30,tzinfo=timezone.utc)

def evidence(**changes):
    fields=dict(
        favorite="Oklahoma",underdog="Kentucky",snapshot_at=T-timedelta(hours=8),
        kickoff=T,sources=("archived pregame offense report","archived pregame injury report"),
        favorite_spread=-7.0,favorite_offensive_drive_sustainability=False,
        favorite_ol_viable=False,favorite_scoring_independent_of_defense_st=False,
        favorite_two_separation_paths=False,dog_offensive_floor=True,
        dog_qb_ol_viable=True,dog_multiple_cover_paths=True,
    )
    fields.update(changes)
    return FavoriteFragilityEvidence(**fields)

def test_kentucky_style_matchup_flags_margin_fragility_without_auto_edge():
    r=favorite_fragility_gate(evidence())
    assert r["status"]=="FAVORITE_MARGIN_FRAGILITY_WATCH"
    assert r["flag"] is True
    assert r["p_raw_delta"]==0
    assert r["lambda_multiplier"]==1

def test_missing_pregame_availability_never_assumed():
    r=favorite_fragility_gate(evidence(dog_qb_ol_viable=None))
    assert r["status"]=="INCOMPLETE_RESEARCH"
    assert r["flag"] is False

def test_dog_without_offensive_floor_not_automatically_favored():
    r=favorite_fragility_gate(evidence(dog_offensive_floor=False))
    assert r["status"]=="NO_FLAG"

def test_postgame_info_cannot_be_used():
    with pytest.raises(ValueError):
        favorite_fragility_gate(evidence(snapshot_at=T+timedelta(minutes=1)))

def test_not_applicable_for_small_favorite():
    r=favorite_fragility_gate(evidence(favorite_spread=-3.5))
    assert r["status"]=="NOT_APPLICABLE"
