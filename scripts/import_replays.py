#!/usr/bin/env python3
"""Import .rofl replay files into json_files/ in ReplayBook-compatible format."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from rofl_extract import parse_replay, write_match_json  # noqa: E402

DEFAULT_OUTPUT = ROOT / "json_files"
BUILD_STATS = ROOT / "scripts" / "build_stats.py"


def import_replays(input_dir: Path, output_dir: Path, overwrite: bool) -> tuple[int, int]:
    imported = 0
    skipped = 0

    for replay_path in sorted(input_dir.glob("*.rofl")):
        output_path = output_dir / f"{replay_path.stem}.json"
        if output_path.exists() and not overwrite:
            skipped += 1
            continue

        payload = parse_replay(replay_path)
        write_match_json(payload, output_path)
        print(f"Imported {replay_path.name} -> {output_path.name}")
        imported += 1

    return imported, skipped


def maybe_rebuild_stats(rebuild: bool) -> None:
    if not rebuild:
        return
    subprocess.run([sys.executable, str(BUILD_STATS)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        type=Path,
        help="Directory containing .rofl replay files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output directory for match JSON (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing json_files entries",
    )
    parser.add_argument(
        "--rebuild-stats",
        action="store_true",
        help="Run scripts/build_stats.py after importing",
    )
    args = parser.parse_args()

    if not args.input.is_dir():
        raise SystemExit(f"Input directory not found: {args.input}")

    imported, skipped = import_replays(args.input, args.output, args.overwrite)
    print(f"Imported {imported} replays, skipped {skipped} existing files")
    maybe_rebuild_stats(args.rebuild_stats)


if __name__ == "__main__":
    main()
