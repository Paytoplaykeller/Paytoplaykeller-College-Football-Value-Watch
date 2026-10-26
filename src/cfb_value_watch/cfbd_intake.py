"""Read-only CollegeFootballData collector. No fabricated pregame features.

CFBD_API_KEY must be supplied via a private runtime environment variable.
The output is raw attributed historical data; it is NOT model-ready until a
pregame feature builder produces each of forecast_v5.FEATURES using data
available as of that particular game's cutoff.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = "https://api.collegefootballdata.com"


class CFBDataError(ValueError):
    pass


def fetch_cfbd(endpoint: str, params: dict, *, api_key: str | None = None) -> dict:
    allowed = {"/games", "/plays", "/games/teams", "/stats/season/advanced"}
    if endpoint not in allowed:
        raise CFBDataError("Endpoint not allowlisted")
    key = api_key or os.getenv("CFBD_API_KEY")
    if not key:
        raise CFBDataError("CFBD_API_KEY missing; no data downloaded")
    if "year" not in params or not isinstance(params["year"], int) or params["year"] < 2000:
        raise CFBDataError("Explicit historical season year required")
    url = ROOT + endpoint + "?" + urlencode(params)
    try:
        with urlopen(Request(url, headers={"Authorization": "Bearer " + key,
                                           "User-Agent": "CFB-Value-Watch/6"}), timeout=25) as resp:
            records = json.load(resp)
    except HTTPError as exc:
        raise CFBDataError(f"CFBD HTTP {exc.code}") from None
    except (URLError, ValueError, TimeoutError):
        raise CFBDataError("CFBD unavailable or invalid JSON") from None
    if not isinstance(records, list):
        raise CFBDataError("Unexpected CFBD response")
    return {"provider": "CollegeFootballData", "endpoint": endpoint, "parameters": params,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "records": records, "raw_research_only": True}


def historical_games(years: tuple[int, ...], *, api_key: str | None = None) -> list[dict]:
    if not years:
        raise CFBDataError("Specify at least one year")
    return [fetch_cfbd("/games", {"year": year, "classification": "fbs"},
                       api_key=api_key) for year in years]
