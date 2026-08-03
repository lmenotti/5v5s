# 5v5s

Stats tracker for custom League of Legends 5v5 games with friends.

## Live dashboard

**https://lmenotti.github.io/5v5s/**

GitHub Pages serves `docs/index.html`, which loads precomputed stats from `docs/data/players.json`.

## Quick start

```bash
# Import new replays (Python — recommended)
python3 scripts/import_replays.py /path/to/Replays --rebuild-stats

# Or regenerate stats after manually adding JSON files
python3 scripts/build_stats.py
```

See [docs/REPLAY_INGESTION.md](docs/REPLAY_INGESTION.md) for replay import options and [docs/AUDIT.md](docs/AUDIT.md) for project history.

## Workflow

1. Import or export replays to `json_files/` ([ReplayBook](https://github.com/fraxiinus/ReplayBook) or `scripts/import_replays.py`)
2. Run `python3 scripts/build_stats.py`
3. Commit `json_files/`, `docs/data/players.json`, and `stats.txt`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/import_replays.py` | Convert `.rofl` replays → `json_files/` |
| `scripts/build_stats.py` | Build dashboard data + `stats.txt` |
| `scripts/analyze_teammates.py` | Teammate win-rate vs self win-rate |
| `scripts/analyze_champion.py` | Per-champion stats (e.g. `Zac`) |
| `scripts/analyze_roles.py` | Role distribution by player |
| `scripts/player_aliases.json` | Summoner name alias map |

Core scripts use **Python 3 stdlib only**. Optional notebook dependencies are in `requirements.txt`.

## Repository layout

| Path | Purpose |
|------|---------|
| `json_files/` | Match data (one JSON file per game) |
| `scripts/` | Import, build, and analysis tooling |
| `docs/data/players.json` | Precomputed stats for the dashboard |
| `docs/` | GitHub Pages site + documentation |
| `notebooks/legacy/` | Archived 2024 exploration notebooks |
| `RoflBatchExporter/` | Optional .NET replay importer |
| `lib/roflxd.cs-master/` | Vendored ROFL parser library |

## Analysis examples

```bash
python3 scripts/analyze_teammates.py
python3 scripts/analyze_champion.py Zac --min-games 2
python3 scripts/analyze_roles.py --player DonutDude17
```
