from datetime import datetime,timedelta,timezone
import pytest
from cfb_value_watch.conference_postseason import (
    CrossConferenceForecast,conference_residual_audit,
    PostseasonAvailability,postseason_gate,
)
T=datetime(2025,12,1,tzinfo=timezone.utc)

def game(i,home="SEC",away="Big Ten",residual=5):
    return CrossConferenceForecast(str(i),T+timedelta(days=i),
        T-timedelta(days=1),home,away,7,7+residual)

def test_cross_conference_strength_residual_is_not_automatic_bonus():
    rows=[game(i,residual=5) for i in range(30)]
    result=conference_residual_audit(rows)
    assert result["conference_residuals"]["SEC"]["mean_margin_residual"]==5
    assert result["conference_residuals"]["Big Ten"]["mean_margin_residual"]==-5
    assert result["no_additive_bonus"] is True

def test_intra_conference_games_excluded():
    result=conference_residual_audit([game(0,home="SEC",away="SEC")])
    assert result["cross_conference_games"]==0

def test_small_sample_is_not_ranked():
    result=conference_residual_audit([game(0)])
    assert result["conference_residuals"]["SEC"]["status"]=="INSUFFICIENT_SAMPLE"

def test_future_forecast_rejected():
    g=game(0)
    with pytest.raises(ValueError):
        conference_residual_audit([CrossConferenceForecast(
            g.game_id,g.kickoff,g.kickoff,g.home_conference,g.away_conference,
            g.predicted_home_margin,g.actual_home_margin)])

def postseason(**changes):
    d=dict(event_id="bowl",as_of=T,kickoff=T+timedelta(days=2),
           qb_status_verified=True,offensive_line_verified=True,
           opt_outs_and_transfers_verified=True,coaching_staff_verified=True,
           defensive_units_verified=True,special_teams_verified=True,
           roster_source="pregame roster report")
    d.update(changes)
    return PostseasonAvailability(**d)

def test_bowl_optouts_missing_blocks_completion():
    assert postseason_gate(postseason(
        opt_outs_and_transfers_verified=False))["status"]=="WATCH_INCOMPLETE_AVAILABILITY"

def test_complete_bowl_roster_not_automatically_bet():
    result=postseason_gate(postseason())
    assert result["status"]=="ROSTER_CHECKS_COMPLETE"
    assert result["bet_authorized"] is False
