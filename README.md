# 5v5s

Stats tracker for custom League of Legends 5v5 games with friends.

## Live dashboard

**https://lmenotti.github.io/5v5s/**

GitHub Pages serves `docs/index.html`, which aggregates match data from `json_files/`.

## How it works

1. Export replays to JSON using [ReplayBook](https://github.com/fraxiinus/ReplayBook)
2. Commit JSON files to `json_files/`
3. The dashboard reads match data via the GitHub API and displays player stats

See [docs/AUDIT.md](docs/AUDIT.md) for a full project audit (August 3, 2026) and planned improvements.

## Local analysis

- `5v5_public_parser.ipynb` — fetch from GitHub and print leaderboards
- `panda.ipynb` — exploratory pandas analysis (teammate synergy, champion stats)

## Repository layout

| Path | Purpose |
|------|---------|
| `json_files/` | Match data (one JSON file per game) |
| `docs/` | GitHub Pages site + audit documentation |
| `RoflBatchExporter/` | Experimental C# batch converter (not used in production) |
| `lib/roflxd.cs-master/` | Vendored ROFL parser library |
