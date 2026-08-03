# 5v5s

Stats tracker for custom League of Legends 5v5 games with friends.

## Live dashboard

**https://lmenotti.github.io/5v5s/**

GitHub Pages serves `docs/index.html`, which aggregates match data from `json_files/`.

## How it works

1. Export replays to JSON using [ReplayBook](https://github.com/fraxiinus/ReplayBook)
2. Commit JSON files to `json_files/`
3. Regenerate aggregated stats: `python3 scripts/build_stats.py`
4. Commit the updated `docs/data/players.json` and `stats.txt`
5. The dashboard loads precomputed stats from `docs/data/players.json` (no GitHub API calls)

See [docs/AUDIT.md](docs/AUDIT.md) for a full project audit (August 3, 2026) and planned improvements.

## Updating stats after new matches

```bash
python3 scripts/build_stats.py
```

This reads `json_files/`, applies aliases from `scripts/player_aliases.json`, and writes:

- `docs/data/players.json` — used by the GitHub Pages dashboard
- `stats.txt` — text leaderboard snapshot

## Local analysis

- `5v5_public_parser.ipynb` — fetch from GitHub and print leaderboards
- `panda.ipynb` — exploratory pandas analysis (teammate synergy, champion stats)

## Repository layout

| Path | Purpose |
|------|---------|
| `json_files/` | Match data (one JSON file per game) |
| `scripts/build_stats.py` | Aggregate match JSON into dashboard + stats.txt |
| `scripts/player_aliases.json` | Summoner name alias map (single source of truth) |
| `docs/data/players.json` | Precomputed stats served by the dashboard |
| `docs/` | GitHub Pages site + audit documentation |
| `RoflBatchExporter/` | Experimental C# batch converter (not used in production) |
| `lib/roflxd.cs-master/` | Vendored ROFL parser library |
