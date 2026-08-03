"""Extract ReplayBook-compatible match JSON from League .rofl replay files."""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

ROFL_V1_SIGNATURE = b"RIOT\x00\x00"
ROFL_V2_SIGNATURE = b"RIOT\x02\x00"
HEADER_SIZE = 288


def _loads_json(raw: str) -> dict:
    """Parse metadata JSON, tolerating integer fields in scientific notation."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        normalized = re.sub(
            r'("gameLength"\s*:\s*)(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)',
            lambda match: f"{match.group(1)}{int(float(match.group(2)))}",
            raw,
        )
        return json.loads(normalized)


def _match_payload(raw_metadata: dict, game_version: str | None = None) -> dict:
    stats_json = raw_metadata.get("statsJson")
    if not stats_json:
        raise ValueError("Replay metadata is missing statsJson")

    participants = json.loads(stats_json)
    version = game_version or raw_metadata.get("gameVersion") or ""
    game_length = raw_metadata.get("gameLength", 0)

    return {
        "gameDuration": int(float(game_length)),
        "gameVersion": version,
        "participants": participants,
    }


def parse_rofl_v1(data: bytes) -> dict:
    if len(data) < HEADER_SIZE:
        raise ValueError("File too small to be a ROFL replay")

    if data[:6] != ROFL_V1_SIGNATURE:
        raise ValueError("Not a ROFL v1 replay")

    lengths = struct.unpack_from("<HI5I", data, 262)
    metadata_length = lengths[3]
    metadata_bytes = data[HEADER_SIZE : HEADER_SIZE + metadata_length]
    raw_metadata = _loads_json(metadata_bytes.decode("utf-8"))
    return _match_payload(raw_metadata)


def parse_rofl_v2(data: bytes) -> dict:
    if len(data) < 32:
        raise ValueError("File too small to be a ROFL2 replay")

    if data[:6] != ROFL_V2_SIGNATURE:
        raise ValueError("Not a ROFL2 replay")

    game_version = data[14:28].decode("utf-8", errors="replace").rstrip("\x00")
    metadata_length = struct.unpack("<i", data[-4:])[0]
    if metadata_length <= 0 or metadata_length + 4 > len(data):
        raise ValueError(f"Invalid ROFL2 metadata length: {metadata_length}")

    metadata_bytes = data[-(metadata_length + 4) : -4]
    raw_metadata = _loads_json(metadata_bytes.decode("utf-8"))
    return _match_payload(raw_metadata, game_version=game_version)


def parse_replay(path: Path) -> dict:
    data = path.read_bytes()
    if data[:6] == ROFL_V1_SIGNATURE:
        payload = parse_rofl_v1(data)
    elif data[:6] == ROFL_V2_SIGNATURE:
        payload = parse_rofl_v2(data)
    else:
        raise ValueError(f"Unsupported replay format: {path.name}")

    payload["matchId"] = path.stem
    return payload


def write_match_json(payload: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
