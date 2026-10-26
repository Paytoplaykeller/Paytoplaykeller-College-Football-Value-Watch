"""2026-only chronological evidence guard for in-season FBS calibration.

Rejects postgame snapshots and all seasons besides 2026.
This is a data contract, not a fitted probability model.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class SeasonEvidence:
    event_id: str
    kickoff: datetime
    stats_as_of: datetime
    season: int
    source: str

def validate_2026_evidence(items: list[SeasonEvidence], *, cutoff: datetime) -> int:
    if cutoff.tzinfo is None:
        raise ValueError("cutoff must be timezone-aware")
    ids=set()
    for item in items:
        if item.season != 2026:
            raise ValueError("Non-2026 statistics rejected")
        if not item.event_id or item.event_id in ids or not item.source.strip():
            raise ValueError("Missing/duplicate event or unattributed source")
        ids.add(item.event_id)
        if item.kickoff.tzinfo is None or item.stats_as_of.tzinfo is None:
            raise ValueError("Timezone-aware timestamps required")
        if not item.stats_as_of < item.kickoff <= cutoff:
            raise ValueError("Pregame snapshot or chronological cutoff violated")
    return len(items)
