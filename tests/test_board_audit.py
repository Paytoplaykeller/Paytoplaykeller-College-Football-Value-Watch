from datetime import datetime, timedelta, timezone
from cfb_value_watch.board_audit import audit_board, verified_bets_only

NOW = datetime(2026, 10, 17, 19, 0, tzinfo=timezone.utc)


def base_review(game_id="FLA-TEX"):
    return {"game_id": game_id, "decision": "WATCH",
            "venue_verified": True, "injury_checked": True,
            "offense_defense_checked": True, "odds_checked": True}


def test_missing_florida_texas_is_caught():
    a = audit_board([{"game_id": "FLA-TEX"}, {"game_id": "ND-BYU"}],
                    [base_review("ND-BYU")], now=NOW)
    assert not a.complete
    assert any(i.game_id == "FLA-TEX" and "UNREVIEWED" in i.reason for i in a.issues)


def test_no_schedule_does_not_claim_coverage():
    assert not audit_board([], [], now=NOW).complete


def test_watch_complete_does_not_create_bet():
    r = base_review()
    a = audit_board([{"game_id": "FLA-TEX"}], [r], now=NOW)
    assert a.complete
    assert verified_bets_only(a, [r]) == []


def test_invalid_bet_missing_independent_probability_blocked():
    r = base_review()
    r.update(decision="BET", price_executable=True,
             quote_time=NOW - timedelta(minutes=3))
    a = audit_board([{"game_id": "FLA-TEX"}], [r], now=NOW)
    assert not a.complete
    assert any("independent_p_raw" in i.reason for i in a.issues)
    assert verified_bets_only(a, [r]) == []


def test_stale_quote_blocks_bet():
    r = base_review()
    r.update({k: True for k in (
        "price_executable", "two_way_market_verified", "independent_p_raw",
        "no_vig_prior_verified", "uncertainty_ev_verified",
        "mandatory_gates_passed", "quarter_kelly_checked",
        "max_price_checked", "bankroll_cap_checked")})
    r.update(decision="BET", quote_time=NOW - timedelta(minutes=20))
    a = audit_board([{"game_id": "FLA-TEX"}], [r], now=NOW)
    assert not a.complete
    assert any("stale" in i.reason for i in a.issues)
