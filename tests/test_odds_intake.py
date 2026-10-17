from datetime import datetime, timezone, timedelta

from cfb_value_watch.odds_intake import paired_cfb_markets, SPORT_KEY


def fixture(now):
    kickoff = (now + timedelta(days=1)).isoformat()
    updated = (now - timedelta(minutes=2)).isoformat()
    return {"events": [{
        "id": "event-1", "sport_key": SPORT_KEY, "commence_time": kickoff,
        "home_team": "Home", "away_team": "Away",
        "bookmakers": [{"key": "hardrockbet_fl", "markets": [
            {"key": "spreads", "last_update": updated, "outcomes": [
                {"name": "Home", "point": -3.5, "price": -110},
                {"name": "Away", "point": 3.5, "price": -110},
            ]},
        ]}],
    }], "retrieved_at": now.isoformat(), "source_url": "https://api.the-odds-api.com"}


def test_exact_spread_pairing():
    now = datetime.now(timezone.utc)
    pairs = paired_cfb_markets(fixture(now), now=now)
    assert len(pairs) == 2
    assert pairs[0]["bookmaker"] == "hardrockbet_fl"
    assert pairs[0]["opposite_price"] == -110


def test_stale_market_rejected():
    now = datetime.now(timezone.utc)
    snapshot = fixture(now)
    snapshot["events"][0]["bookmakers"][0]["markets"][0]["last_update"] = (
        now - timedelta(hours=1)).isoformat()
    assert paired_cfb_markets(snapshot, now=now) == []


def test_missing_opposite_contract_rejected():
    now = datetime.now(timezone.utc)
    snapshot = fixture(now)
    snapshot["events"][0]["bookmakers"][0]["markets"][0]["outcomes"][1]["point"] = 4.5
    assert paired_cfb_markets(snapshot, now=now) == []


def test_started_event_rejected():
    now = datetime.now(timezone.utc)
    snapshot = fixture(now)
    snapshot["events"][0]["commence_time"] = (now - timedelta(minutes=1)).isoformat()
    assert paired_cfb_markets(snapshot, now=now) == []


def test_comparison_never_claims_hardrock_executable():
    from cfb_value_watch.odds_intake import compare_public_markets
    now = datetime.now(timezone.utc)
    snap = fixture(now)
    first = snap["events"][0]["bookmakers"][0]
    first["key"] = "fanduel"
    second = {"key": "draftkings", "markets": [{
        "key": "spreads", "last_update": (now-timedelta(minutes=2)).isoformat(),
        "outcomes": [{"name": "Home", "point": -3.5, "price": -105},
                     {"name": "Away", "point": 3.5, "price": -115}]
    }]}
    snap["events"][0]["bookmakers"].append(second)
    rows = compare_public_markets(snap, now=now)
    assert len(rows) == 2
    assert all(r["status"] == "WATCH" and r["hardrock_status"] == "UNVERIFIED" for r in rows)
    home = next(r for r in rows if r["selection"] == "Home")
    assert home["best_public_book"] == "draftkings"
    assert home["best_public_price"] == -105


def test_different_spread_numbers_not_falsely_compared():
    from cfb_value_watch.odds_intake import compare_public_markets
    now = datetime.now(timezone.utc)
    snap = fixture(now)
    snap["events"][0]["bookmakers"][0]["key"] = "fanduel"
    snap["events"][0]["bookmakers"].append({
        "key": "draftkings", "markets": [{
            "key": "spreads", "last_update": (now-timedelta(minutes=2)).isoformat(),
            "outcomes": [{"name": "Home", "point": -4.5, "price": -110},
                         {"name": "Away", "point": 4.5, "price": -110}]
        }]
    })
    assert compare_public_markets(snap, now=now) == []
