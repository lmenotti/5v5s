"""Shared helpers for loading and aggregating match JSON data."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ALIASES = ROOT / "scripts" / "player_aliases.json"
DEFAULT_INPUT = ROOT / "json_files"


def load_aliases(path: Path = DEFAULT_ALIASES) -> dict[str, str]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def primary_name(name: str, aliases: dict[str, str]) -> str:
    return aliases.get(name, name)


def parse_int(value, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_match(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def iter_matches(json_dir: Path = DEFAULT_INPUT) -> list[dict]:
    matches: list[dict] = []
    for json_path in sorted(json_dir.glob("*.json")):
        match = load_match(json_path)
        if match.get("participants"):
            matches.append(match)
    return matches


def iter_participant_rows(
    json_dir: Path = DEFAULT_INPUT, aliases: dict[str, str] | None = None
) -> list[dict]:
    if aliases is None:
        aliases = load_aliases()

    rows: list[dict] = []
    for match in iter_matches(json_dir):
        for player in match["participants"]:
            if not player.get("NAME"):
                continue
            row = dict(player)
            row["matchId"] = match.get("matchId")
            row["gameDuration"] = match.get("gameDuration")
            row["gameVersion"] = match.get("gameVersion")
            row["NAME"] = primary_name(player["NAME"], aliases)
            rows.append(row)
    return rows


def is_win(result: str | None) -> bool:
    return result == "Win"


def empty_player() -> dict:
    return {
        "matches": 0,
        "wins": 0,
        "losses": 0,
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "penta_kills": 0,
        "teammates": {},
        "skins": {},
        "teammateWinRates": [],
        "WinRate": 0.0,
        "kda": 0.0,
        "dpm": 0.0,
        "cspm": 0.0,
        "total_cspm": 0.0,
        "damage": 0,
        "time_played": 0,
        "cs": 0,
        "time_played_cs": 0,
    }


def ensure_player(player_stats: dict[str, dict], name: str) -> dict:
    if name not in player_stats:
        player_stats[name] = empty_player()
    return player_stats[name]


def finalize_rates(stats: dict) -> None:
    matches = stats["matches"]
    stats["WinRate"] = (100 * stats["wins"] / matches) if matches else 0.0
    deaths = stats["deaths"]
    stats["kda"] = (
        (stats["kills"] + stats["assists"]) / deaths
        if deaths > 0
        else float(stats["kills"] + stats["assists"])
    )
    stats["dpm"] = (
        stats["damage"] / (stats["time_played"] / 60)
        if stats["time_played"] > 0
        else 0.0
    )
    stats["cspm"] = (
        stats["cs"] / (stats["time_played_cs"] / 60)
        if stats["time_played_cs"] > 0
        else 0.0
    )
    stats["total_cspm"] = (
        stats["cs"] / (stats["time_played"] / 60) if stats["time_played"] > 0 else 0.0
    )


def aggregate_player_stats(
    json_dir: Path = DEFAULT_INPUT, aliases: dict[str, str] | None = None
) -> tuple[dict[str, dict], int]:
    if aliases is None:
        aliases = load_aliases()

    player_stats: dict[str, dict] = {}
    match_count = 0

    for match in iter_matches(json_dir):
        participants = match["participants"]
        match_count += 1

        for player in participants:
            raw_name = player.get("NAME")
            if not raw_name:
                continue

            name = primary_name(raw_name, aliases)
            team = player.get("TEAM")
            stats = ensure_player(player_stats, name)

            stats["matches"] += 1
            stats["kills"] += parse_int(player.get("CHAMPIONS_KILLED"))
            stats["assists"] += parse_int(player.get("ASSISTS"))
            stats["deaths"] += parse_int(player.get("NUM_DEATHS"))
            stats["penta_kills"] += parse_int(player.get("PENTA_KILLS"))
            stats["time_played"] += parse_int(player.get("TIME_PLAYED"))
            stats["damage"] += parse_int(player.get("TOTAL_DAMAGE_DEALT_TO_CHAMPIONS"))

            minions = parse_int(player.get("MINIONS_KILLED"))
            neutral = parse_int(player.get("NEUTRAL_MINIONS_KILLED"))
            time_played = parse_int(player.get("TIME_PLAYED"))
            if time_played > 0 and (minions + neutral) / (time_played / 60) > 2:
                stats["cs"] += minions + neutral
                stats["time_played_cs"] += time_played

            skin = player.get("SKIN")
            if skin:
                stats["skins"][skin] = stats["skins"].get(skin, 0) + 1

            if is_win(player.get("WIN")):
                stats["wins"] += 1
            else:
                stats["losses"] += 1

            finalize_rates(stats)

            for teammate in participants:
                teammate_raw = teammate.get("NAME")
                if (
                    teammate.get("TEAM") == team
                    and teammate_raw
                    and teammate_raw != raw_name
                ):
                    teammate_name = primary_name(teammate_raw, aliases)
                    stats["teammates"][teammate_name] = (
                        stats["teammates"].get(teammate_name, 0) + 1
                    )
                    teammate_entry = ensure_player(player_stats, teammate_name)
                    teammate_win_rate = (
                        teammate_entry["wins"] / teammate_entry["matches"]
                        if teammate_entry["matches"]
                        else 0.0
                    )
                    stats["teammateWinRates"].append(teammate_win_rate)

    return player_stats, match_count


def build_teammate_counts(
    json_dir: Path = DEFAULT_INPUT, aliases: dict[str, str] | None = None
) -> dict[str, dict[str, int]]:
    if aliases is None:
        aliases = load_aliases()

    teammate_counts: dict[str, dict[str, int]] = {}

    for match in iter_matches(json_dir):
        teams: dict[str, list[str]] = {}
        for player in match["participants"]:
            raw_name = player.get("NAME")
            team = player.get("TEAM")
            if not raw_name or team is None:
                continue
            name = primary_name(raw_name, aliases)
            teams.setdefault(str(team), []).append(name)

        for players in teams.values():
            for player_name in players:
                teammate_counts.setdefault(player_name, {})
                for teammate_name in players:
                    if teammate_name != player_name:
                        teammate_counts[player_name][teammate_name] = (
                            teammate_counts[player_name].get(teammate_name, 0) + 1
                        )

    return teammate_counts
