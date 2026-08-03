# Legacy Notebooks

These notebooks were used during initial exploration (2024). They have been replaced by scripts in `../scripts/`.

| Notebook | Replacement |
|----------|-------------|
| `5v5_public_parser.ipynb` | `scripts/build_stats.py`, `scripts/analyze_teammates.py` |
| `5v5_private_parser.ipynb` | `scripts/build_stats.py` (broken draft; do not use) |
| `panda.ipynb` | `scripts/analyze_champion.py`, `scripts/analyze_roles.py`, `scripts/match_data.py` |

To run the old notebooks, install optional dependencies from the repo root:

```bash
pip install -r requirements.txt
```

Update hardcoded paths in the notebooks if you still need them — the scripts use repo-relative paths by default.
