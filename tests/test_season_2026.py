from datetime import datetime, timezone, timedelta
import pytest
from cfb_value_watch.season_2026 import SeasonEvidence,validate_2026_evidence

K=datetime(2026,10,24,17,tzinfo=timezone.utc)
def sample(): return SeasonEvidence("game1",K,K-timedelta(days=2),2026,"verified team stats")
def test_2026_pregame_evidence_accepted():
    assert validate_2026_evidence([sample()],cutoff=K)==1
def test_2025_rejected():
    x=sample()
    with pytest.raises(ValueError,match="Non-2026"):
        validate_2026_evidence([SeasonEvidence(x.event_id,x.kickoff,x.stats_as_of,2025,x.source)],cutoff=K)
def test_late_stats_rejected():
    with pytest.raises(ValueError,match="Pregame"):
        validate_2026_evidence([SeasonEvidence("game1",K,K+timedelta(hours=1),2026,"source")],cutoff=K)
def test_duplicate_rejected():
    with pytest.raises(ValueError,match="duplicate"):
        validate_2026_evidence([sample(),sample()],cutoff=K)
