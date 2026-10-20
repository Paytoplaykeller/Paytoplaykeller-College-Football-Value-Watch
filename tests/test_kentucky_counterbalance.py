from cfb_value_watch.gates import offensive_survival_counterbalance


def test_counterbalance_does_not_inflate_unvalidated_confidence():
    r = offensive_survival_counterbalance(
        home_underdog=True,
        clustered_defensive_injuries=True,
        sustainable_offense=True,
        ball_security=True,
        discipline=True,
        special_teams_field_position=True,
        late_game_resilience=True,
        opponent_defensive_weakness=True,
    )
    assert r.lambda_multiplier == 1.0
    assert r.stake_cap is None
    assert "research-only" in r.reasons[0]
