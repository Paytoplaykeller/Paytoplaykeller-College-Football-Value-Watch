"""Keyless historical CFB datasets from SportsDataverse GitHub Releases.

This is archive retrieval only. ESPN-derived betting records may contain
closing lines: they MUST NOT be presented as executable pregame prices and
must not enter forecast_v5 feature vectors. Games/play-by-play must be
transformed into strictly as-of historical features separately.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone

BASE = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"
ASSETS = {
    "betting": ("espn_cfb_betting", "betting_{year}.parquet"),
    "pbp": ("espn_cfb_pbp", "play_by_play_{year}.parquet"),
    "schedules": ("cfb_schedules", "cfb_schedules_{year}.parquet"),
}


class HistoricalArchiveError(ValueError):
    pass


def asset_url(dataset: str, year: int) -> str:
    if dataset not in ASSETS or type(year) is not int or not 2004 <= year <= 2025:
        raise HistoricalArchiveError("Unsupported dataset or completed historical year")
    tag, template = ASSETS[dataset]
    return f"{BASE}/{tag}/{template.format(year=year)}"


def download_archive(dataset: str, year: int, target_dir: str, *, limit_bytes=500_000_000) -> dict:
    url = asset_url(dataset, year)
    dest = Path(target_dir)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / url.rsplit("/", 1)[-1]
    if path.exists():
        raise HistoricalArchiveError("Refusing to overwrite existing archive")
    total = 0
    digest = hashlib.sha256()
    try:
        with urlopen(Request(url, headers={"User-Agent": "CFB-Value-Watch/archive-research"}), timeout=50) as response:
            with path.open("xb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > limit_bytes:
                        raise HistoricalArchiveError("Archive size exceeded limit")
                    digest.update(chunk)
                    output.write(chunk)
        if total < 4 or path.read_bytes()[:4] != b"PAR1":
            raise HistoricalArchiveError("Download was not a parquet file")
    except (HTTPError, URLError, OSError, TimeoutError, HistoricalArchiveError):
        path.unlink(missing_ok=True)
        raise HistoricalArchiveError("Historical archive unavailable or invalid") from None
    info = {
        "dataset": dataset, "year": year, "source": url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sha256": digest.hexdigest(), "size_bytes": total,
        "path": str(path), "historical_only": True, "forecast_features_ready": False,
        "bet_now_approval": False,
    }
    (dest / (path.name + ".provenance.json")).write_text(json.dumps(info, indent=2))
    return info
