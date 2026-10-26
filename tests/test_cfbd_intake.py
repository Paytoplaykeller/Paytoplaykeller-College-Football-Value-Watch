from unittest.mock import patch
import pytest
from cfb_value_watch.cfbd_intake import fetch_cfbd, historical_games, CFBDataError
from cfb_value_watch.odds_intake import BOOKMAKERS, compare_public_markets


def test_missing_cfbd_key_fails_closed():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(CFBDataError, match="CFBD_API_KEY"):
            historical_games((2023, 2024))


def test_endpoint_allowlist_rejects_other_endpoints():
    with pytest.raises(CFBDataError, match="allowlisted"):
        fetch_cfbd("/private", {"year": 2025}, api_key="not-real")


def test_invalid_year_rejected():
    with pytest.raises(CFBDataError, match="year"):
        fetch_cfbd("/games", {"year": "2025"}, api_key="not-real")


def test_hardrock_fl_in_quote_provider_list_but_not_executable():
    assert "hardrockbet_fl" in BOOKMAKERS
    assert compare_public_markets({"events": []}) == []
