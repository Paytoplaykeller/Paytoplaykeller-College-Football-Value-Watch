"""Collect source-attributed historical FBS games and betting lines from CFBD.

Requires CFBD_API_KEY, never writes credentials, never backfills pregame injury
or advanced-stat snapshots from postgame sources. Produces raw archives for a
separate point-in-time feature builder and validation pipeline.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone

BASE = "https://api.collegefootballdata.com"
ENDPOINTS = {"games": "/games", "lines": "/lines"}
class DataSourceError(RuntimeError):
    pass

def retrieve(year: int, category: str, *, key: str | None = None) -> dict:
    if category not in ENDPOINTS or year < 2013 or year > datetime.now(timezone.utc).year:
        raise DataSourceError("Invalid historical category or year")
    secret=key or os.environ.get("CFBD_API_KEY")
    if not secret:
        raise DataSourceError("CFBD_API_KEY missing; no historical data collected")
    url=BASE+ENDPOINTS[category]+"?"+urlencode({"year":year,"seasonType":"both"})
    try:
        with urlopen(Request(url,headers={
            "Authorization":"Bearer "+secret,
            "Accept":"application/json",
            "User-Agent":"CFB-Value-Watch/5 historical-validation"
        }),timeout=40) as response:
            payload=json.load(response)
    except HTTPError as exc:
        raise DataSourceError(f"CFBD HTTP {exc.code} for {category} {year}") from None
    except (URLError, TimeoutError, ValueError):
        raise DataSourceError(f"CFBD request failed for {category} {year}") from None
    if not isinstance(payload,list):
        raise DataSourceError(f"Unexpected {category} response")
    return {"provider":"CollegeFootballData.com","endpoint":ENDPOINTS[category],
            "year":year,"retrieved_at":datetime.now(timezone.utc).isoformat(),
            "count":len(payload),"rows":payload}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--start-year",type=int,default=2018)
    parser.add_argument("--end-year",type=int,default=2025)
    parser.add_argument("--output",default="data/raw_cfbd")
    args=parser.parse_args()
    if args.end_year < args.start_year:
        parser.error("end-year must be >= start-year")
    directory=Path(args.output)
    directory.mkdir(parents=True,exist_ok=True)
    for year in range(args.start_year,args.end_year+1):
        for category in ENDPOINTS:
            payload=retrieve(year,category)
            dest=directory/f"{category}_{year}.json"
            dest.write_text(json.dumps(payload,indent=2),encoding="utf-8")
            print(f"{category} {year}: {payload['count']} rows -> {dest}")
    print("RAW DATA ONLY. No point-in-time features or validated BET forecast produced.")

if __name__=="__main__":
    main()
