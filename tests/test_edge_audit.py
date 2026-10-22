from datetime import datetime, timedelta, timezone
import pytest
from cfb_value_watch.edge_audit import HistoricalDecision, evaluate_ticket, audit_decisions

T=datetime(2025,10,17,tzinfo=timezone.utc)

def sample(**changes):
    d=dict(game_id="g1",kickoff=T,forecast_at=T-timedelta(hours=12),
           odds_at=T-timedelta(hours=1),selection="Home +3.5",
           market="spread",line=3.5,offered_american=-110,
           no_vig_market_prior=.5,adjusted_win_probability=.57,
           adjusted_push_probability=0.0,outcome="LOSS",
           model_version="frozen_v1",forecast_source="pregame_snapshot",
           price_source="book_quote")
    d.update(changes)
    return HistoricalDecision(**d)

def test_actual_ev_and_quarter_kelly():
    r=evaluate_ticket(sample())
    assert round(r["expected_value"],6)==round(.57*(100/110)-.43,6)
    assert r["quarter_kelly_ceiling"]>0
    assert r["realized_unit_return"]==-1

def test_plus_200_price_and_push_math():
    r=evaluate_ticket(sample(offered_american=200,adjusted_win_probability=.4,
                             adjusted_push_probability=.1,outcome="PUSH"))
    assert round(r["expected_value"],6)==.3
    assert r["realized_unit_return"]==0

def test_no_future_data_or_untimestamped_forecast():
    with pytest.raises(ValueError):
        evaluate_ticket(sample(forecast_at=T+timedelta(minutes=1)))
    with pytest.raises(ValueError):
        evaluate_ticket(sample(odds_at=T+timedelta(minutes=1)))

def test_duplicate_tickets_do_not_inflate_skill():
    with pytest.raises(ValueError,match="Duplicate game"):
        audit_decisions([sample(),sample(selection="Home +4.5")],min_games=1,min_seasons=1)

def test_small_sample_never_approved():
    r=audit_decisions([sample()],min_games=200)
    assert r["status"]=="INSUFFICIENT_EVIDENCE"
    assert r["approved_for_live_betting"] is False

def test_market_comparison_without_claiming_profit():
    records=[sample(game_id=f"g{i}",kickoff=T+timedelta(days=i*100),
                    forecast_at=T+timedelta(days=i*100)-timedelta(hours=12),
                    odds_at=T+timedelta(days=i*100)-timedelta(hours=1),
                    outcome="WIN" if i%2 else "LOSS") for i in range(8)]
    r=audit_decisions(records,min_games=5,min_seasons=2)
    assert r["status"]=="RESEARCH_ONLY"
    assert "market_brier" in r and "model_brier" in r
    assert r["approved_for_live_betting"] is False

def test_push_needs_three_way_scoring():
    records=[sample(game_id=f"g{i}",kickoff=T+timedelta(days=i*100),
                    forecast_at=T+timedelta(days=i*100)-timedelta(hours=12),
                    odds_at=T+timedelta(days=i*100)-timedelta(hours=1),
                    adjusted_push_probability=.1) for i in range(8)]
    r=audit_decisions(records,min_games=5,min_seasons=2)
    assert r["status"]=="REQUIRES_THREE_WAY_SCORING"
