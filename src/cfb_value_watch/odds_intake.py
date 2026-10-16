"""Read-only college football odds intake using the NFL agent's Odds API provider.

No sportsbook login, betting access, or credential storage. Requires ODDS_API_KEY
in the execution environment. Only upcoming events and fresh paired markets.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import os

SPORT_KEY = "americanfootball_ncaaf"
ROOT = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds"
BOOKMAKERS = "hardrockbet_fl,fanduel,draftkings,betmgm,pinnacle"


class OddsIntakeError(ValueError):
    pass


def fetch_cfb_odds(*, api_key: str | None = None, markets: str = "h2h,spreads,totals") -> dict:
    key = api_key or os.environ.get("ODDS_API_KEY")
    if not key:
        raise OddsIntakeError("ODDS_API_KEY is not configured")
    params = urlencode({
        "apiKey": key, "bookmakers": BOOKMAKERS, "markets": markets,
        "oddsFormat": "american", "dateFormat": "iso",
    })
    try:
        with urlopen(Request(ROOT + "?" + params,
                             headers={"User-Agent": "CFB-Value-Watch/5 research-only"}),
                     timeout=20) as response:
            events = json.load(response)
    except HTTPError as exc:
        raise OddsIntakeError(f"Odds provider returned HTTP {exc.code}") from None
    except (URLError, TimeoutError, ValueError):
        raise OddsIntakeError("Odds provider unavailable or returned invalid JSON") from None
    if not isinstance(events, list):
        raise OddsIntakeError("Unexpected odds payload")
    return {"events": events, "source_url": ROOT,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "provider": "The Odds API", "read_only": True}


def paired_cfb_markets(snapshot: dict, *, now: datetime | None = None,
                       max_age_seconds: int = 900) -> list[dict]:
    """Produce exact-contract pairs only. Missing/old prices never imply zero."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise OddsIntakeError("now must be timezone aware")
    pairs = []
    for event in snapshot["events"]:
        if event.get("sport_key") != SPORT_KEY:
            continue
        try:
            kickoff = datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if kickoff <= now:
            continue
        teams = (event.get("home_team"), event.get("away_team"))
        for book in event.get("bookmakers", []):
            for market in book.get("markets", []):
                if market.get("key") not in {"h2h", "spreads", "totals"}:
                    continue
                try:
                    stamp = datetime.fromisoformat(
                        (market.get("last_update") or book["last_update"]).replace("Z", "+00:00"))
                    age = (now - stamp).total_seconds()
                except (KeyError, ValueError, TypeError):
                    continue
                if not 0 <= age <= max_age_seconds:
                    continue
                outcomes = market.get("outcomes", [])
                for side in outcomes:
                    name, point = side.get("name"), side.get("point")
                    key = market["key"]
                    if key == "h2h":
                        opposite = [o for o in outcomes if o.get("name") in teams and o.get("name") != name]
                        valid = name in teams and len(outcomes) == 2
                    elif key == "spreads":
                        opposite = [o for o in outcomes if o.get("name") in teams
                                    and o.get("name") != name and point is not None
                                    and o.get("point") == -point]
                        valid = name in teams and point is not None
                    else:
                        opposite = [o for o in outcomes if o.get("name") == ("Under" if name == "Over" else "Over")
                                    and o.get("point") == point]
                        valid = name in {"Over", "Under"} and point is not None
                    duplicates = [o for o in outcomes if o.get("name") == name and o.get("point") == point]
                    if not valid or len(opposite) != 1 or len(duplicates) != 1:
                        continue
                    price, other = side.get("price"), opposite[0].get("price")
                    if not all(isinstance(v, int) and not isinstance(v, bool) and abs(v) >= 100
                               for v in (price, other)):
                        continue
                    pairs.append({
                        "event_id": event["id"], "kickoff": event["commence_time"],
                        "home_team": teams[0], "away_team": teams[1],
                        "bookmaker": book["key"], "market": key,
                        "selection": name, "line": point, "price": price,
                        "opposite_price": other, "published_at": stamp.isoformat(),
                        "retrieved_at": snapshot["retrieved_at"], "source_url": snapshot["source_url"],
                    })
    return pairs
