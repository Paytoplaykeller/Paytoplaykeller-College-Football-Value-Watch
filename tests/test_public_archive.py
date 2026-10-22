import pytest
from cfb_value_watch.public_archive import asset_url, HistoricalArchiveError

def test_2024_betting_archive():
    assert asset_url("betting", 2024) == (
        "https://github.com/sportsdataverse/sportsdataverse-data/releases/"
        "download/espn_cfb_betting/betting_2024.parquet"
    )

def test_2025_pbp_archive():
    assert asset_url("pbp", 2025).endswith(
        "/espn_cfb_pbp/play_by_play_2025.parquet"
    )

def test_no_future_or_unsupported_dataset():
    for typ, year in (("betting",2026),("fake",2024),("pbp",1999)):
        with pytest.raises(HistoricalArchiveError):
            asset_url(typ,year)
