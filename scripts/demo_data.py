"""Demo-site transforms: anonymized names and league-wide aggregates."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from match_data import is_win, iter_matches, load_aliases, parse_int, primary_name

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


def attach_player_forms(
    player_stats: dict[str, dict], json_dir: Path, aliases: dict[str, str], name_map: dict[str, str]
) -> None:
    history: dict[str, list[int]] = defaultdict(list)
    matches = sorted(iter_matches(json_dir), key=lambda match: str(match.get("matchId", "")))

    for match in matches:
        for player in match["participants"]:
            raw_name = player.get("NAME")
            if not raw_name:
                continue
            public = display_name(primary_name(raw_name, aliases), name_map)
            history[public].append(1 if is_win(player.get("WIN")) else 0)

    for name, results in history.items():
        if name in player_stats:
            player_stats[name]["form"] = results[-10:]


def _kda_value(kills: int, deaths: int, assists: int) -> float:
    if deaths > 0:
        return (kills + assists) / deaths
    return float(kills + assists)


def compute_head_to_head(
    json_dir: Path, aliases: dict[str, str], name_map: dict[str, str]
) -> dict[str, dict]:
    h2h: dict[str, dict] = defaultdict(
        lambda: {"together": 0, "togetherWins": 0, "versus": 0, "wins": {}}
    )

    def pair_key(name_a: str, name_b: str) -> str:
        return "|".join(sorted((name_a, name_b)))

    for match in iter_matches(json_dir):
        teams: dict[str, list[tuple[str, bool]]] = defaultdict(list)
        for player in match["participants"]:
            raw_name = player.get("NAME")
            team = player.get("TEAM")
            if not raw_name or team is None:
                continue
            public = display_name(primary_name(raw_name, aliases), name_map)
            teams[str(team)].append((public, is_win(player.get("WIN"))))

        team_lists = list(teams.values())
        for team in team_lists:
            for (name_a, won_a), (name_b, won_b) in combinations(team, 2):
                if name_a == name_b:
                    continue
                entry = h2h[pair_key(name_a, name_b)]
                entry["together"] += 1
                if won_a and won_b:
                    entry["togetherWins"] += 1

        if len(team_lists) == 2:
            for name_a, won_a in team_lists[0]:
                for name_b, won_b in team_lists[1]:
                    if name_a == name_b:
                        continue
                    entry = h2h[pair_key(name_a, name_b)]
                    entry["versus"] += 1
                    winner = name_a if won_a else name_b if won_b else None
                    if winner:
                        entry["wins"][winner] = entry["wins"].get(winner, 0) + 1

    return dict(h2h)


def compute_records(
    json_dir: Path,
    aliases: dict[str, str],
    name_map: dict[str, str],
    player_stats: dict[str, dict],
) -> dict:
    best_kills = {"value": 0}
    best_damage = {"value": 0}
    best_kda = {"value": 0.0}
    best_streaks: dict[str, int] = defaultdict(int)
    current_streaks: dict[str, int] = defaultdict(int)
    longest_game = {"minutes": 0.0}
    shortest_game = {"minutes": float("inf")}

    matches = sorted(iter_matches(json_dir), key=lambda match: str(match.get("matchId", "")))

    for match in matches:
        duration_ms = parse_int(match.get("gameDuration"))
        if duration_ms:
            minutes = round(duration_ms / 1000 / 60, 1)
            if minutes > longest_game["minutes"]:
                longest_game = {
                    "minutes": minutes,
                    "matchId": str(match.get("matchId", "")),
                }
            if minutes < shortest_game["minutes"]:
                shortest_game = {
                    "minutes": minutes,
                    "matchId": str(match.get("matchId", "")),
                }

        for player in match["participants"]:
            raw_name = player.get("NAME")
            if not raw_name:
                continue
            public = display_name(primary_name(raw_name, aliases), name_map)
            kills = parse_int(player.get("CHAMPIONS_KILLED"))
            deaths = parse_int(player.get("NUM_DEATHS"))
            assists = parse_int(player.get("ASSISTS"))
            damage = parse_int(player.get("TOTAL_DAMAGE_DEALT_TO_CHAMPIONS"))
            champion = player.get("SKIN") or "Unknown"
            kda = _kda_value(kills, deaths, assists)
            match_id = str(match.get("matchId", ""))
            won = is_win(player.get("WIN"))

            if kills > best_kills["value"]:
                best_kills = {
                    "value": kills,
                    "player": public,
                    "champion": champion,
                    "matchId": match_id,
                }
            if damage > best_damage["value"]:
                best_damage = {
                    "value": damage,
                    "player": public,
                    "champion": champion,
                    "matchId": match_id,
                }
            if kda > best_kda["value"]:
                best_kda = {
                    "value": round(kda, 2),
                    "player": public,
                    "champion": champion,
                    "matchId": match_id,
                }

            if won:
                current_streaks[public] += 1
                best_streaks[public] = max(best_streaks[public], current_streaks[public])
            else:
                current_streaks[public] = 0

    best_streak_player = max(best_streaks, key=best_streaks.get) if best_streaks else None
    penta_leader = max(
        player_stats.items(),
        key=lambda item: (item[1].get("penta_kills", 0), item[1]["matches"]),
    )

    highlights = [
        {
            "id": "kills",
            "label": "Most kills · single game",
            "value": str(best_kills.get("value", 0)),
            "player": best_kills.get("player", "—"),
            "detail": best_kills.get("champion", ""),
        },
        {
            "id": "damage",
            "label": "Most damage · single game",
            "value": f"{best_damage.get('value', 0):,}",
            "player": best_damage.get("player", "—"),
            "detail": best_damage.get("champion", ""),
        },
        {
            "id": "kda",
            "label": "Best KDA · single game",
            "value": str(best_kda.get("value", 0)),
            "player": best_kda.get("player", "—"),
            "detail": best_kda.get("champion", ""),
        },
        {
            "id": "streak",
            "label": "Longest win streak",
            "value": str(best_streaks.get(best_streak_player, 0) if best_streak_player else 0),
            "player": best_streak_player or "—",
            "detail": "consecutive wins",
        },
        {
            "id": "penta",
            "label": "Career pentakills",
            "value": str(penta_leader[1].get("penta_kills", 0)),
            "player": penta_leader[0],
            "detail": "all-time",
        },
        {
            "id": "longest",
            "label": "Longest game",
            "value": f"{longest_game.get('minutes', 0)}m",
            "player": "—",
            "detail": f"match {longest_game.get('matchId', '')}",
        },
        {
            "id": "shortest",
            "label": "Shortest game",
            "value": f"{shortest_game.get('minutes', 0)}m",
            "player": "—",
            "detail": f"match {shortest_game.get('matchId', '')}",
        },
    ]

    return {"highlights": highlights}


def compute_mvp(leaderboard: list[dict], min_games: int = 20) -> dict | None:
    eligible = [row for row in leaderboard if row["matches"] >= min_games]
    if not eligible:
        eligible = leaderboard
    if not eligible:
        return None

    mvp = max(eligible, key=lambda row: (row["winRate"], row["kda"], row["matches"]))
    return {
        "name": mvp["name"],
        "winRate": mvp["winRate"],
        "kda": mvp["kda"],
        "matches": mvp["matches"],
        "dpm": mvp["dpm"],
    }


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
    attach_player_forms(public_stats, json_dir, aliases, name_map)
    leaderboard = build_leaderboard(public_stats)
    return {
        "leaderboard": leaderboard,
        "championMeta": compute_champion_meta(json_dir),
        "duos": compute_duos(json_dir, aliases, name_map),
        "totals": compute_league_totals(public_stats, match_count, json_dir),
        "records": compute_records(json_dir, aliases, name_map, public_stats),
        "mvp": compute_mvp(leaderboard),
        "headToHead": compute_head_to_head(json_dir, aliases, name_map),
    }
