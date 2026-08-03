#!/usr/bin/env python3
"""Compare each player's win rate to the average win rate of their teammates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from match_data import (  # noqa: E402
    DEFAULT_ALIASES,
    DEFAULT_INPUT,
    aggregate_player_stats,
    build_teammate_counts,
    load_aliases,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES)
    parser.add_argument("--player", help="Only show results for this player")
    args = parser.parse_args()

    aliases = load_aliases(args.aliases)
    player_stats, _ = aggregate_player_stats(args.input, aliases)
    teammate_counts = build_teammate_counts(args.input, aliases)

    rows: list[tuple[str, float, float, float, int]] = []
    for player_name, stats in player_stats.items():
        if args.player and player_name != args.player:
            continue

        total_games = 0
        weighted_teammate_wr = 0.0
        for teammate, games_together in teammate_counts.get(player_name, {}).items():
            teammate_wr = player_stats[teammate]["WinRate"]
            weighted_teammate_wr += teammate_wr * games_together
            total_games += games_together

        avg_teammate_wr = (
            weighted_teammate_wr / total_games if total_games else 0.0
        )
        delta = avg_teammate_wr - stats["WinRate"]
        rows.append((player_name, avg_teammate_wr, stats["WinRate"], delta, stats["matches"]))

    rows.sort(key=lambda row: row[4], reverse=True)

    for player_name, teammate_wr, self_wr, delta, games in rows:
        print(
            f"{player_name}: teammates {teammate_wr:.2f}% vs self {self_wr:.2f}% "
            f"(delta {delta:+.2f}%) over {games} games"
        )


if __name__ == "__main__":
    main()
