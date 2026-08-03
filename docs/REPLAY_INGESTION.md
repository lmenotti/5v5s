# Replay Ingestion

## Decision (August 3, 2026)

**Primary path:** `scripts/import_replays.py` — portable Python extractor for ROFL and ROFL2 files.

**Secondary paths:**

- **ReplayBook GUI** — still supported; export JSON manually and commit to `json_files/`
- **`RoflBatchExporter/`** — optional .NET 7 CLI using the vendored roflxd library

All paths produce the same match JSON shape:

```json
{
  "matchId": "5143654212",
  "gameDuration": 1802981,
  "gameVersion": "14.21.630.3012",
  "participants": [ ... ]
}
```

The `matchId` comes from the replay filename stem (League replays are named by match ID).

## Recommended workflow

```bash
# Import replays from your League client replay folder
python3 scripts/import_replays.py /path/to/Replays --rebuild-stats

# Or import only
python3 scripts/import_replays.py /path/to/Replays

# Regenerate dashboard data separately
python3 scripts/build_stats.py
```

Common replay locations:

- **Windows:** `%USERPROFILE%\\Documents\\League of Legends\\Replays`
- **Linux (Lutris/Wine):** varies by install; pass the directory explicitly

## .NET alternative

Requires [.NET 7 SDK](https://dotnet.microsoft.com/download):

```bash
dotnet run --project RoflBatchExporter -- /path/to/Replays json_files --overwrite
```

## Format notes

- ROFL metadata embeds player stats as JSON in `statsJson`; field names match ReplayBook exports (`NAME`, `SKIN`, `WIN`, etc.).
- `SKIN` is the champion name, not a cosmetic skin.
- `WIN` values include `Win`, `Fail`, and `LeaverFail`.

## Validation

After importing, verify the corpus:

```bash
python3 scripts/build_stats.py
python3 -c "
import json, pathlib
for path in pathlib.Path('json_files').glob('*.json'):
    data = json.loads(path.read_text())
    assert len(data['participants']) == 10, path.name
print('OK')
"
