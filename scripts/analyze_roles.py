#!/usr/bin/env python3
"""Show role distribution for one or all players."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from match_data import DEFAULT_ALIASES, DEFAULT_INPUT, load_aliases, primary_name  # noqa: E402
from match_data import iter_matches  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--aliases", type=Path, default=DEFAULT_ALIASES)
    parser.add_argument("--player", help="Only show results for this player")
    args = parser.parse_args()

    aliases = load_aliases(args.aliases)
    role_counts: dict[str, Counter[str]] = {}

    for match in iter_matches(args.input):
        for player in match["participants"]:
            raw_name = player.get("NAME")
            role = player.get("INDIVIDUAL_POSITION") or "UNKNOWN"
            if not raw_name:
                continue
            name = primary_name(raw_name, aliases)
            if args.player and name != args.player:
                continue
            role_counts.setdefault(name, Counter())[role] += 1

    if not role_counts:
        print("No role data found")
        return

    for name in sorted(role_counts, key=lambda n: sum(role_counts[n].values()), reverse=True):
        total = sum(role_counts[name].values())
        print(f"{name} ({total} games):")
        for role, count in role_counts[name].most_common():
            pct = 100 * count / total
            print(f"  {role}: {count} ({pct:.0f}%)")


if __name__ == "__main__":
    main()
