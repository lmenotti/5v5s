"""Demo-site transforms: anonymized names and league-wide aggregates."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from match_data import is_win, iter_matches, load_aliases, primary_name

DEFAULT_DEMO_NAMES = Path(__file__).resolve().parent / "demo_names.json"


def load_demo_names(path: Path = DEFAULT_DEMO_NAMES) -> dict[str, str]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def display_name(real_name: str, name_map: dict[str, str]) -> str:
    if real_name in name_map:
        return name_map[real_name]
    slug = real_name.upper().replace(" ", "-")[:16]
    return f"UNIT-{slug}"


def anonymize_player_stats(
    player_stats: dict[str, dict], name_map: dict[str, str]
) -> dict[str, dict]:
    anonymized: dict[str, dict] = {}

    for real_name, stats in player_stats.items():
        public_name = display_name(real_name, name_map)
        entry = dict(stats)
        entry["teammates"] = {
            display_name(teammate, name_map): count
            for teammate, count in stats.get("teammates", {}).items()
        }
        anonymized[public_name] = entry

    return anonymized


def build_leaderboard(player_stats: dict[str, dict]) -> list[dict]:
    rows = []
    for name, stats in player_stats.items():
        rows.append(
            {
                "name": name,
                "matches": stats["matches"],
                "winRate": round(stats["WinRate"], 2),
                "kda": round(stats["kda"], 2),
                "dpm": round(stats["dpm"], 1),
                "wins": stats["wins"],
                "losses": stats["losses"],
            }
        )
    rows.sort(key=lambda row: (row["matches"], row["winRate"]), reverse=True)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def compute_champion_meta(json_dir: Path) -> list[dict]:
    games = Counter()
    wins = Counter()

    for match in iter_matches(json_dir):
        for player in match["participants"]:
            champion = player.get("SKIN")
            if not champion:
                continue
            games[champion] += 1
            if is_win(player.get("WIN")):
                wins[champion] += 1

    rows = []
    for champion, count in games.most_common():
        rows.append(
            {
                "champion": champion,
                "games": count,
                "winRate": round(100 * wins[champion] / count, 1) if count else 0.0,
            }
        )
    return rows


def compute_duos(
    json_dir: Path, aliases: dict[str, str], name_map: dict[str, str], min_games: int = 5
) -> list[dict]:
    duo_stats: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"games": 0, "wins": 0}
    )

    for match in iter_matches(json_dir):
        teams: dict[str, list[tuple[str, bool]]] = defaultdict(list)
        for player in match["participants"]:
            raw_name = player.get("NAME")
            team = player.get("TEAM")
            if not raw_name or team is None:
                continue
            canonical = primary_name(raw_name, aliases)
            public = display_name(canonical, name_map)
            teams[str(team)].append((public, is_win(player.get("WIN"))))

        for team_rows in teams.values():
            for (name_a, won_a), (name_b, won_b) in combinations(team_rows, 2):
                if name_a == name_b:
                    continue
                key = tuple(sorted((name_a, name_b)))
                duo_stats[key]["games"] += 1
                if won_a and won_b:
                    duo_stats[key]["wins"] += 1

    rows = []
    for (name_a, name_b), stats in duo_stats.items():
        if stats["games"] < min_games:
            continue
        rows.append(
            {
                "playerA": name_a,
                "playerB": name_b,
                "games": stats["games"],
                "winRate": round(100 * stats["wins"] / stats["games"], 1),
            }
        )

    rows.sort(key=lambda row: (row["winRate"], row["games"]), reverse=True)
    return rows[:15]


def compute_league_totals(
    player_stats: dict[str, dict], match_count: int, json_dir: Path
) -> dict:
    total_kills = sum(stats["kills"] for stats in player_stats.values())
    total_damage = sum(stats["damage"] for stats in player_stats.values())
    durations = [
        match.get("gameDuration", 0)
        for match in iter_matches(json_dir)
        if match.get("gameDuration")
    ]
    avg_duration_ms = sum(durations) / len(durations) if durations else 0

    return {
        "matches": match_count,
        "players": len(player_stats),
        "totalKills": total_kills,
        "totalDamage": total_damage,
        "avgGameMinutes": round(avg_duration_ms / 1000 / 60, 1),
    }


def build_league_payload(
    player_stats: dict[str, dict],
    match_count: int,
    json_dir: Path,
    aliases: dict[str, str],
    name_map: dict[str, str],
) -> dict:
    public_stats = anonymize_player_stats(player_stats, name_map)
    return {
        "leaderboard": build_leaderboard(public_stats),
        "championMeta": compute_champion_meta(json_dir),
        "duos": compute_duos(json_dir, aliases, name_map),
        "totals": compute_league_totals(public_stats, match_count, json_dir),
    }
