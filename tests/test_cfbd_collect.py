import pytest
from cfb_value_watch.cfbd_collect import retrieve, DataSourceError


def test_historical_collector_rejects_missing_key(monkeypatch):
    monkeypatch.delenv("CFBD_API_KEY", raising=False)
    with pytest.raises(DataSourceError, match="CFBD_API_KEY"):
        retrieve(2024, "games")


def test_historical_collector_rejects_bad_category():
    with pytest.raises(DataSourceError):
        retrieve(2024, "postgame_fabricated_features", key="not_used")


def test_historical_collector_rejects_invalid_year():
    with pytest.raises(DataSourceError):
        retrieve(2012, "games", key="not_used")
