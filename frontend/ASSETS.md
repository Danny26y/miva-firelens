# Frontend asset inventory

Generated from verified standard-quality processed data; no correction applied.

| File under `public/data/` | Bytes | Contents |
|---|---:|---|
| `weekly_fire_counts.json` | 230,328 | 1,337 positive weekly sensor records with status |
| `comparison.json` | 6,901 | Descriptive comparison summaries |
| `paired_weeks.json` | 64,145 | 410 positive paired full weeks |
| `provenance.json` | 9,268 | Source SHA-256 hashes, date bounds, missing-record week lists, credits |

Total: **310,642 bytes**, approximately 303 KiB. All are normal Git-sized files.
Source calendar: 203,590 bytes; source comparison: 111,389 bytes. Both parsed as
valid JSON. The handoff omits source record duplication and local machine paths.
Tests verify totals, keys, source equality where available and pair consistency.
