#!/usr/bin/env python3
"""Show per-player stats for a specific champion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from match_data import DEFAULT_ALIASES, DEFAULT_INPUT, load_aliases, parse_int, primary_name  # noqa: E402
from match_data import iter_matches, is_win  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("champion", help="Champion name (SKIN field), e.g. Zac")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES)
    parser.add_argument("--player", help="Only show results for this player")
    parser.add_argument("--min-games", type=int, default=1, help="Minimum games on champion")
    args = parser.parse_args()

    aliases = load_aliases(args.aliases)
    stats: dict[str, dict] = {}

    for match in iter_matches(args.input):
        for player in match["participants"]:
            if player.get("SKIN") != args.champion or not player.get("NAME"):
                continue

            name = primary_name(player["NAME"], aliases)
            if args.player and name != args.player:
                continue

            entry = stats.setdefault(
                name,
                {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0},
            )
            entry["games"] += 1
            entry["kills"] += parse_int(player.get("CHAMPIONS_KILLED"))
            entry["deaths"] += parse_int(player.get("NUM_DEATHS"))
            entry["assists"] += parse_int(player.get("ASSISTS"))
            if is_win(player.get("WIN")):
                entry["wins"] += 1

    if not stats:
        print(f"No games found for champion {args.champion}")
        return

    print(f"Champion: {args.champion}")
    rows = sorted(stats.items(), key=lambda item: item[1]["games"], reverse=True)
    for name, entry in rows:
        if entry["games"] < args.min_games:
            continue
        win_rate = 100 * entry["wins"] / entry["games"]
        avg_kills = entry["kills"] / entry["games"]
        kda = (
            (entry["kills"] + entry["assists"]) / entry["deaths"]
            if entry["deaths"] > 0
            else float(entry["kills"] + entry["assists"])
        )
        print(f"  {name}: {entry['games']} games, {win_rate:.2f}% WR, "
              f"{avg_kills:.2f} kills/game, {kda:.2f} KDA")


if __name__ == "__main__":
    main()
