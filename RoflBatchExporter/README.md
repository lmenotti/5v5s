Optional .NET batch importer. Prefer `scripts/import_replays.py` when Python is available.

## Requirements

- [.NET 7 SDK](https://dotnet.microsoft.com/download)

## Usage

From the repository root:

```bash
dotnet run --project RoflBatchExporter -- /path/to/Replays json_files --overwrite
```

Arguments:

1. Input directory containing `.rofl` files
2. Output directory (defaults to `json_files/` when omitted)
3. `--overwrite` to replace existing JSON files

Output matches the ReplayBook-compatible schema documented in [docs/REPLAY_INGESTION.md](../docs/REPLAY_INGESTION.md).
