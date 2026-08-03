#!/usr/bin/env python3
"""Aggregate match JSON into player stats for the dashboard and stats.txt."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ALIASES = ROOT / "scripts" / "player_aliases.json"
DEFAULT_INPUT = ROOT / "json_files"
DEFAULT_STATS = ROOT / "stats.txt"
DEFAULT_PLAYERS_JSON = ROOT / "docs" / "data" / "players.json"


def load_aliases(path: Path) -> dict[str, str]:
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
        stats["cs"] / (stats["time_played"] / 60)
        if stats["time_played"] > 0
        else 0.0
    )


def aggregate_matches(json_dir: Path, aliases: dict[str, str]) -> tuple[dict[str, dict], int]:
    player_stats: dict[str, dict] = {}
    match_count = 0

    for json_path in sorted(json_dir.glob("*.json")):
        with json_path.open(encoding="utf-8") as handle:
            match = json.load(handle)

        participants = match.get("participants")
        if not participants:
            continue

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

            if player.get("WIN") == "Win":
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


def write_stats_txt(player_stats: dict[str, dict], output_path: Path) -> None:
    lines: list[str] = []
    sorted_players = sorted(
        player_stats.items(), key=lambda item: item[1]["matches"], reverse=True
    )

    for player_name, stats in sorted_players:
        matches = stats["matches"]
        avg_kills = stats["kills"] / matches if matches else 0.0
        lines.append(f"Player: {player_name}  Win Rate: {stats['WinRate']:.2f}%  "
                       f"Games Played: {matches}  "
                       f"Average Kills per Match: {avg_kills:.2f}  "
                       f"Average KDA: {stats['kda']:.2f}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_players_json(
    player_stats: dict[str, dict], match_count: int, output_path: Path
) -> None:
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "matchCount": match_count,
        "players": player_stats,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES)
    parser.add_argument("--stats-out", type=Path, default=DEFAULT_STATS)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_PLAYERS_JSON)
    args = parser.parse_args()

    aliases = load_aliases(args.aliases)
    player_stats, match_count = aggregate_matches(args.input, aliases)

    write_stats_txt(player_stats, args.stats_out)
    write_players_json(player_stats, match_count, args.json_out)

    print(f"Processed {match_count} matches for {len(player_stats)} players")
    print(f"Wrote {args.stats_out}")
    print(f"Wrote {args.json_out}")


if __name__ == "__main__":
    main()
