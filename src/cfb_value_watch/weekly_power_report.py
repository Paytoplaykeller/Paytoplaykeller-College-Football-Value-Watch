"""Weekly 2026 FBS opponent-network snapshot, advisory only.

Source: SportsDataverse public ESPN-derived schedule parquet releases.
Scores may appear in downloads after games finish. Historical snapshots use
kickoff + six-hour embargo, preventing inclusion of same-week outcomes.
All "strength of wins" numbers are retrospective AS-OF ratings, not features
that were knowable before the earlier games.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .replay_oct17 import COLS, URL
from .schedule_network import NetworkGame, fit_network


def schedule_through(as_of: datetime) -> pd.DataFrame:
    if as_of.tzinfo is None:
        raise ValueError("Timezone-aware snapshot required")
    frames = []
    for year in range(max(2024, as_of.year - 2), as_of.year + 1):
        frame = pd.read_parquet(URL.format(year=year))
        missing = set(COLS) - set(frame.columns)
        if missing:
            raise ValueError(f"{year} schedule missing {sorted(missing)}")
        frames.append(frame[COLS])
    df = pd.concat(frames, ignore_index=True)
    df["kickoff"] = pd.to_datetime(df.start_date, utc=True, errors="coerce")
    df = df[
        (df.fbs_game == True) &
        df.kickoff.notna() &
        df.home_id.notna() & df.away_id.notna() &
        df.home_conference.notna() & df.away_conference.notna() &
        df.home_team.notna() & df.away_team.notna()
    ].copy()
    df["game_id"] = df.game_id.astype(str)
    if df.game_id.duplicated().any():
        raise ValueError("Duplicate FBS schedule game ID")
    return df


def finished(df: pd.DataFrame, as_of: datetime) -> pd.DataFrame:
    """Only games scheduled to have finished at least six hours ago."""
    cutoff = pd.Timestamp(as_of.astimezone(timezone.utc) - timedelta(hours=6))
    return df[(df.completed == True) &
              (df.kickoff <= cutoff) &
              df.home_points.notna() &
              df.away_points.notna()].copy()


def network_games(df: pd.DataFrame) -> list[NetworkGame]:
    result = []
    for g in df.itertuples(index=False):
        result.append(NetworkGame(
            game_id=str(g.game_id), kickoff=g.kickoff.to_pydatetime(),
            season=int(g.season),
            home_id=str(g.home_id), away_id=str(g.away_id),
            home_conference=str(g.home_conference),
            away_conference=str(g.away_conference),
            neutral=bool(g.neutral_site),
            home_points=int(g.home_points), away_points=int(g.away_points)))
    return result


def current_season_teams(df: pd.DataFrame, season: int) -> dict[str, dict]:
    """Team display names and conference identities from current season only."""
    latest = {}
    upcoming = df[df.season == season].sort_values("kickoff")
    for g in upcoming.itertuples(index=False):
        for side in ("home", "away"):
            key = str(getattr(g, side + "_id"))
            latest[key] = {
                "id": key, "name": str(getattr(g, side + "_team")),
                "conference": str(getattr(g, side + "_conference")),
            }
    return latest


def cross_conference_results(games: pd.DataFrame) -> dict:
    overall = defaultdict(lambda: {"wins": 0, "losses": 0, "games": 0})
    pairs = defaultdict(lambda: {"first_wins": 0, "second_wins": 0, "games": 0})
    for g in games.itertuples(index=False):
        hc, ac = str(g.home_conference), str(g.away_conference)
        if hc == ac or int(g.home_points) == int(g.away_points):
            continue
        winner, loser = (hc, ac) if g.home_points > g.away_points else (ac, hc)
        overall[winner]["wins"] += 1
        overall[loser]["losses"] += 1
        overall[winner]["games"] += 1
        overall[loser]["games"] += 1
        first, second = sorted([hc, ac])
        row = pairs[(first, second)]
        row["first_wins" if winner == first else "second_wins"] += 1
        row["games"] += 1
    return {
        "raw_records": dict(sorted(overall.items())),
        "direct_pair_records": [
            {"first": a, "second": b, **r}
            for (a, b), r in sorted(pairs.items())
        ],
        "caution": "Opponent quality and schedule selection are NOT controlled by raw W-L."
    }


def generate(df: pd.DataFrame, as_of: datetime) -> dict:
    if as_of.tzinfo is None:
        raise ValueError("Timezone-aware as_of required")
    prev_as_of = as_of - timedelta(days=7)
    now_games = finished(df, as_of)
    prev_games = finished(df, prev_as_of)
    last_completed = now_games.kickoff.max()
    if pd.isna(last_completed):
        raise ValueError("No completed FBS games in imported schedule")
    latest = last_completed.to_pydatetime()
    if as_of - latest > timedelta(days=8):
        raise ValueError(f"2026 schedule appears stale: latest={latest.isoformat()}")
    season = as_of.year
    current = now_games[now_games.season == season].copy()
    recent = current[current.kickoff > pd.Timestamp(prev_as_of)]
    if len(current) < 200 or len(recent) < 15:
        raise ValueError(
            f"Incomplete current-season or weekly FBS feed: "
            f"season={len(current)}, last7d={len(recent)}")
    now_ratings = fit_network(network_games(now_games), as_of, min_games=100)
    prev_ratings = fit_network(network_games(prev_games), prev_as_of, min_games=100)
    names = current_season_teams(df, season)
    this_counts, prev_counts = defaultdict(int), defaultdict(int)
    results = defaultdict(lambda: {"wins": 0, "losses": 0,
                                   "quality_wins": [], "losses_detail": []})
    for part, target in ((current, this_counts),
                         (prev_games[prev_games.season == season], prev_counts)):
        for g in part.itertuples(index=False):
            target[str(g.home_id)] += 1
            target[str(g.away_id)] += 1
    strength = {}
    old_strength = {}
    for key, label in names.items():
        conf = label["conference"]
        strength[key] = (now_ratings.team_ratings.get(key, 0.0) +
                         now_ratings.conference_effects.get(conf, 0.0))
        old_strength[key] = (prev_ratings.team_ratings.get(key, 0.0) +
                             prev_ratings.conference_effects.get(conf, 0.0))
    for g in current.itertuples(index=False):
        home, away = str(g.home_id), str(g.away_id)
        if g.home_points == g.away_points:
            continue
        winner, loser = (home, away) if g.home_points > g.away_points else (away, home)
        results[winner]["wins"] += 1
        results[loser]["losses"] += 1
        results[winner]["quality_wins"].append({
            "opponent": names.get(loser, {"name": loser})["name"],
            "opponent_current_power": round(strength.get(loser, 0.0), 2),
            "game_id": str(g.game_id),
        })
        results[loser]["losses_detail"].append({
            "opponent": names.get(winner, {"name": winner})["name"],
            "opponent_current_power": round(strength.get(winner, 0.0), 2),
            "game_id": str(g.game_id),
        })
    teams = []
    for key, label in names.items():
        if this_counts[key] < 3 or prev_counts[key] < 3:
            continue
        wins = sorted(results[key]["quality_wins"],
                      key=lambda w: w["opponent_current_power"], reverse=True)
        losses = sorted(results[key]["losses_detail"],
                        key=lambda w: w["opponent_current_power"])
        teams.append({
            "id": key, "name": label["name"], "conference": label["conference"],
            "current_season_fbs_games": this_counts[key],
            "current_season_fbs_wins": results[key]["wins"],
            "current_season_fbs_losses": results[key]["losses"],
            "power_now": round(strength[key], 2),
            "power_prior_week": round(old_strength[key], 2),
            "power_change": round(strength[key] - old_strength[key], 2),
            "quality_wins_asof": wins[:3],
            "losses_to_lower_rated_opponents_asof": [
                loss for loss in losses if loss["opponent_current_power"] < strength[key]
            ][:3],
        })
    teams.sort(key=lambda x: x["power_now"], reverse=True)
    for rank, row in enumerate(teams, 1):
        row["power_rank_now"] = rank
    # Complete next 7-day schedule. Margins use current roster-agnostic model
    # and must not be interpreted as current bookmaker lines.
    soon = df[(df.season == season) &
              (df.kickoff > pd.Timestamp(as_of)) &
              (df.kickoff <= pd.Timestamp(as_of + timedelta(days=7)))].copy()
    fixtures = []
    for g in soon.sort_values("kickoff").itertuples(index=False):
        home, away = str(g.home_id), str(g.away_id)
        if this_counts[home] < 3 or this_counts[away] < 3:
            continue
        now_p = now_ratings.project(home, away, str(g.home_conference),
                                    str(g.away_conference), bool(g.neutral_site))
        old_p = prev_ratings.project(home, away, str(g.home_conference),
                                     str(g.away_conference), bool(g.neutral_site))
        margin = now_p["projected_home_margin"]
        fixtures.append({
            "game_id": str(g.game_id),
            "kickoff_utc": g.kickoff.isoformat(),
            "away": str(g.away_team), "home": str(g.home_team),
            "away_conference": str(g.away_conference),
            "home_conference": str(g.home_conference),
            "model_home_margin_now": round(margin, 2),
            "model_home_margin_prior_week": round(old_p["projected_home_margin"], 2),
            "model_margin_change": round(
                margin - old_p["projected_home_margin"], 2),
            "model_favored": (str(g.home_team) if margin > 0
                              else str(g.away_team)),
            "status": "RESEARCH_ONLY_NOT_BET",
            "availability": "NOT_VERIFIED",
            "bookmaker_odds": "NOT_IMPORTED",
        })
    movers_up = sorted(teams, key=lambda r: r["power_change"], reverse=True)[:12]
    movers_down = sorted(teams, key=lambda r: r["power_change"])[:12]
    report = {
        "status": "RESEARCH_ONLY_NOT_BET",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of.isoformat(),
        "prior_as_of": prev_as_of.isoformat(),
        "source": "SportsDataverse cfb_schedules 2024-2026 parquet",
        "data_coverage": {
            "current_season_fbs_completed_games": len(current),
            "newly_eligible_week_fbs_completed_games": len(recent),
            "latest_completed_kickoff_utc": latest.isoformat(),
            "model_training_games": now_ratings.training_games,
            "teams_with_three_or_more_games_both_weeks": len(teams),
            "upcoming_fbs_fixtures_rated": len(fixtures),
        },
        "conference_effect_diagnostic": {
            "estimated_effects_points": {
                k: round(v, 2) for k, v in now_ratings.conference_effects.items()},
            "warning": "Joint team/conference ridge coefficients are not independent conference rankings. Do not add twice."
        },
        "cross_conference_results_2026": cross_conference_results(current),
        "top_rated": teams[:25],
        "biggest_weekly_gains": movers_up,
        "biggest_weekly_declines": movers_down,
        "teams": teams,
        "upcoming_games": fixtures,
        "limit": [
            "All outputs are research-only; no sportsbook prices, odds, calibrated ATS edge or bankroll actions",
            "Team ratings include conferences once; not separate additive conference bonuses",
            "Raw interconference W-L is schedule-confounded",
            "Quality of victories uses opponent ratings measured AS OF NOW; do not replay into pregame models",
            "No FCS wins/losses counted in current-season FBS-only records",
            "No team injuries, lineups, transfers, coaching updates, postseason opt-outs or bookmaker quotes ingested",
            "Only pre-snapshot game scores (kickoff + 6h) are used; later-edited public historical feeds lack verified ingest timestamps",
        ],
    }
    return report


def run(out: Path, as_of: datetime) -> dict:
    report = generate(schedule_through(as_of), as_of)
    out.mkdir(parents=True, exist_ok=True)
    (out / "weekly_power_ratings.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    spotlight = {"Kentucky", "BYU", "Ohio State", "Miami", "Alabama",
                 "Georgia", "Tennessee", "Ole Miss", "Indiana", "Texas"}
    interesting = [r for r in report["teams"] if r["name"] in spotlight]
    upcoming = [r for r in report["upcoming_games"] if
                r["home"] in spotlight or r["away"] in spotlight]
    summary = {
        "status": report["status"], "as_of": report["as_of"],
        "data_coverage": report["data_coverage"],
        "top_rated": [
            {k: r[k] for k in ("name", "conference", "power_rank_now",
                              "power_now", "power_change")}
            for r in report["top_rated"][:15]],
        "biggest_gains": [
            {k: r[k] for k in ("name", "conference", "power_change")}
            for r in report["biggest_weekly_gains"][:8]],
        "biggest_declines": [
            {k: r[k] for k in ("name", "conference", "power_change")}
            for r in report["biggest_weekly_declines"][:8]],
        "spotlight": interesting,
        "spotlight_fixtures": upcoming,
        "conference_raw_results": {
            k: v for k, v in report["cross_conference_results_2026"]["raw_records"].items()
            if k in {"SEC", "Big Ten", "Big 12", "ACC"}
        },
        "conference_coefficients": {
            k: v for k, v in
            report["conference_effect_diagnostic"]["estimated_effects_points"].items()
            if k in {"SEC", "Big Ten", "Big 12", "ACC"}
        },
    }
    (out / "weekly_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of",
                        help="Timezone-aware ISO-8601 timestamp (default now UTC)")
    parser.add_argument("--out", default="data/weekly_power")
    args = parser.parse_args()
    frozen = (datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
              if args.as_of else datetime.now(timezone.utc))
    run(Path(args.out), frozen)
