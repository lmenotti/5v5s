#!/usr/bin/env python3
"""Aggregate match JSON into player stats for the dashboard and stats.txt."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from demo_data import (  # noqa: E402
    DEFAULT_DEMO_NAMES,
    anonymize_player_stats,
    attach_player_forms,
    build_league_payload,
    load_demo_names,
)
from match_data import (  # noqa: E402
    DEFAULT_ALIASES,
    DEFAULT_INPUT,
    aggregate_player_stats,
    load_aliases,
)

DEFAULT_STATS = ROOT / "stats.txt"
DEFAULT_PLAYERS_JSON = ROOT / "docs" / "data" / "players.json"
DEFAULT_LEAGUE_JSON = ROOT / "docs" / "data" / "league.json"


def write_stats_txt(player_stats: dict[str, dict], output_path: Path) -> None:
    lines: list[str] = []
    sorted_players = sorted(
        player_stats.items(), key=lambda item: item[1]["matches"], reverse=True
    )

    for player_name, stats in sorted_players:
        matches = stats["matches"]
        avg_kills = stats["kills"] / matches if matches else 0.0
        lines.append(
            f"Player: {player_name}  Win Rate: {stats['WinRate']:.2f}%  "
            f"Games Played: {matches}  "
            f"Average Kills per Match: {avg_kills:.2f}  "
            f"Average KDA: {stats['kda']:.2f}"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(payload: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def write_players_json(
    player_stats: dict[str, dict], match_count: int, output_path: Path
) -> None:
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "matchCount": match_count,
        "players": player_stats,
    }
    write_json(payload, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES)
    parser.add_argument("--demo-names", type=Path, default=DEFAULT_DEMO_NAMES)
    parser.add_argument("--stats-out", type=Path, default=DEFAULT_STATS)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_PLAYERS_JSON)
    parser.add_argument("--league-out", type=Path, default=DEFAULT_LEAGUE_JSON)
    parser.add_argument(
        "--no-anonymize",
        action="store_true",
        help="Write real names to docs JSON (default anonymizes for public demo)",
    )
    args = parser.parse_args()

    aliases = load_aliases(args.aliases)
    name_map = load_demo_names(args.demo_names)
    player_stats, match_count = aggregate_player_stats(args.input, aliases)

    write_stats_txt(player_stats, args.stats_out)

    public_stats = (
        player_stats
        if args.no_anonymize
        else anonymize_player_stats(player_stats, name_map)
    )
    if not args.no_anonymize:
        attach_player_forms(public_stats, args.input, aliases, name_map)
    write_players_json(public_stats, match_count, args.json_out)

    league_payload = build_league_payload(
        player_stats, match_count, args.input, aliases, name_map
    )
    league_payload["generatedAt"] = datetime.now(timezone.utc).isoformat()
    write_json(league_payload, args.league_out)

    print(f"Processed {match_count} matches for {len(player_stats)} players")
    print(f"Wrote {args.stats_out} (real names)")
    print(f"Wrote {args.json_out} ({'real' if args.no_anonymize else 'demo'} names)")
    print(f"Wrote {args.league_out}")


if __name__ == "__main__":
    main()
