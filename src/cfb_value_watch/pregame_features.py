"""Chronology-safe preparation of observed game/team efficiency features.

Only play-by-play from games finished before each target's feature timestamp
is used. Injury/availability cannot be inferred from game logs: absent those
source-attributed pregame values, a row is NOT v5-forecast-ready.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import isfinite

OBSERVED_FIELDS = (
    "home_off_epa", "away_off_epa", "home_def_epa_allowed", "away_def_epa_allowed",
    "home_success_rate", "away_success_rate",
    "home_havoc_allowed", "away_havoc_allowed",
    "home_havoc_created", "away_havoc_created",
    "home_explosive_rate", "away_explosive_rate",
    "home_rest_days", "away_rest_days", "neutral_site",
)
AVAILABILITY_FIELDS = (
    "home_qb_availability", "away_qb_availability",
    "home_ol_availability", "away_ol_availability",
    "home_def_availability", "away_def_availability",
)


def parse_timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _rate(value):
    if isinstance(value, bool):
        return float(value)
    try:
        z = float(value)
        return z if isfinite(z) else 0.0
    except (ValueError, TypeError):
        return 0.0


def _game_team_stats(plays):
    totals = defaultdict(lambda: dict(plays=0, epa=0.0, successes=0, havoc=0, explosive=0))
    for p in plays:
        offense = str(p.get("pos_team_id") or p.get("pos_team") or "")
        defense = str(p.get("def_pos_team_id") or p.get("def_pos_team") or "")
        if not offense or not defense or offense == defense:
            continue
        # Exclude special teams and other non-scrimmage records.
        rush, pas = bool(p.get("rush")), bool(p.get("pass"))
        if not (rush or pas):
            continue
        epa = p.get("EPA")
        if epa is None:
            continue
        try:
            epa = float(epa)
            if not isfinite(epa):
                continue
        except (ValueError, TypeError):
            continue
        offense_row = totals[offense]
        defense_row = totals[defense + "::DEF"]
        success = bool(p.get("firstD_by_poss")) or bool(p.get("td_play"))
        havoc = bool(p.get("sack")) or bool(p.get("int")) or bool(p.get("fumble_vec"))
        yards = _rate(p.get("yds_rushed") if rush else p.get("yds_receiving"))
        explosive = yards >= (12 if rush else 20)
        offense_row["plays"] += 1
        offense_row["epa"] += epa
        offense_row["successes"] += int(success)
        offense_row["havoc"] += int(havoc)
        offense_row["explosive"] += int(explosive)
        defense_row["plays"] += 1
        defense_row["epa"] += epa
        defense_row["successes"] += int(success)
        defense_row["havoc"] += int(havoc)
        defense_row["explosive"] += int(explosive)
    return totals


def _summarize(recent, suffix=""):
    group = [g[suffix] for g in recent if suffix in g and g[suffix].get("plays", 0) > 0]
    n = sum(x["plays"] for x in group)
    if not n:
        return None
    return dict(
        epa=sum(x["epa"] for x in group) / n,
        success=sum(x["successes"] for x in group) / n,
        havoc=sum(x["havoc"] for x in group) / n,
        explosive=sum(x["explosive"] for x in group) / n,
    )


def build_pregame_snapshots(schedules, play_by_play, *, minimum_prior_games=3, window=5):
    """Return only partial observed feature rows; do not invent availability.

    Schedules include season+game_id+team labels+final scores+start date.
    Rows are evaluated before updating team records with that game's plays.
    A four-hour post-kickoff quarantine prevents treating an unfinished game
    as complete. Sources must be snapshotted historically for real backtests.
    """
    plays_by_id = defaultdict(list)
    for p in play_by_play:
        ident = str(p.get("game_id", ""))
        if ident:
            plays_by_id[ident].append(p)
    completed = []
    for s in schedules:
        if s.get("fbs_game") is not True or s.get("completed") is not True:
            continue
        if s.get("home_points") is None or s.get("away_points") is None:
            continue
        try:
            kickoff = parse_timestamp(s["start_date"])
        except (KeyError, ValueError, AttributeError):
            continue
        if kickoff.tzinfo is None:
            continue
        completed.append((kickoff, s))
    completed.sort(key=lambda x: (x[0], str(x[1]["game_id"])))
    history = defaultdict(list)
    output = []
    for kickoff, s in completed:
        home = str(s.get("home_id") or s.get("home_team") or "")
        away = str(s.get("away_id") or s.get("away_team") or "")
        game_id = str(s["game_id"])
        if not home or not away:
            continue
        # No prior same-kickoff games can leak into this game's features.
        h = [x for x in history[home] if x[0] + timedelta(hours=4) < kickoff]
        a = [x for x in history[away] if x[0] + timedelta(hours=4) < kickoff]
        observed = {}
        if len(h) >= minimum_prior_games and len(a) >= minimum_prior_games:
            ho = _summarize([r[1] for r in h[-window:]], "")
            hd = _summarize([r[1] for r in h[-window:]], "::DEF")
            ao = _summarize([r[1] for r in a[-window:]], "")
            ad = _summarize([r[1] for r in a[-window:]], "::DEF")
            if all(x is not None for x in (ho, hd, ao, ad)):
                observed = dict(
                    home_off_epa=ho["epa"], away_off_epa=ao["epa"],
                    home_def_epa_allowed=hd["epa"], away_def_epa_allowed=ad["epa"],
                    home_success_rate=ho["success"], away_success_rate=ao["success"],
                    home_havoc_allowed=ho["havoc"], away_havoc_allowed=ao["havoc"],
                    home_havoc_created=hd["havoc"], away_havoc_created=ad["havoc"],
                    home_explosive_rate=ho["explosive"], away_explosive_rate=ao["explosive"],
                    home_rest_days=(kickoff-h[-1][0]).total_seconds()/86400,
                    away_rest_days=(kickoff-a[-1][0]).total_seconds()/86400,
                    neutral_site=float(bool(s.get("neutral_site"))),
                )
        output.append({
            "game_id":game_id, "kickoff":kickoff.isoformat(),
            "as_of":(kickoff-timedelta(minutes=1)).isoformat(),
            "home_team":s.get("home_team"), "away_team":s.get("away_team"),
            "features":observed,
            "missing_features":list(AVAILABILITY_FIELDS) if observed else
                list(OBSERVED_FIELDS + AVAILABILITY_FIELDS),
            "final_home_margin":int(s["home_points"])-int(s["away_points"]),
            "source":"sportsdataverse ESPN schedules and PBP",
            "bet_now_eligible":False,
        })
        totals = _game_team_stats(plays_by_id[game_id])
        # Prevent this game's records from entering any earlier forecast.
        history[home].append((kickoff, {"":totals.get(home,{}), "::DEF":totals.get(home+"::DEF",{})}))
        history[away].append((kickoff, {"":totals.get(away,{}), "::DEF":totals.get(away+"::DEF",{})}))
    return output
