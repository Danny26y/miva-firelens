# First verified Kaduna weekly detection dataset

Run date: 2026-11-14. Status: **VERIFIED** for the supplied observations and
documented selection. This does not certify complete satellite coverage.

## Recursive download inventory

Paths are relative to `C:\Users\Daniel\Desktop\miva-firelens`.
Each folder contains two CSVs and one 89-byte `Readme.txt`. Both readmes link to
[NASA's official download readme](https://firms.modaps.eosdis.nasa.gov/download/Readme.txt).
No request email, requested polygon or explicit requested date interval is
included. The inventory includes every file and SHA-256 in
`data/processed/download_audit.json`; all original hashes were verified unchanged.

| Original CSV path | Bytes | Rows | Observed dates inclusive | Kaduna rows |
|---|---:|---:|---|---:|
| `DL_FIRE_M-C61_848524/fire_archive_M-C61_848524.csv` | 9,002,827 | 116,487 | 2024-11-01–2026-08-31 | 7,875 |
| `DL_FIRE_M-C61_848524/fire_nrt_M-C61_848524.csv` | 471,644 | 5,525 | 2026-09-01–2026-11-14 | 126 |
| `DL_FIRE_SV-C2_848525/fire_archive_SV-C2_848525.csv` | 63,722,723 | 808,083 | 2024-11-01–2026-07-31 | 57,241 |
| `DL_FIRE_SV-C2_848525/fire_nrt_SV-C2_848525.csv` | 1,768,504 | 21,342 | 2026-08-01–2026-11-02 | 202 |

All four CSVs have these columns, in order:
`latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite,
instrument, confidence, version, bright_t31, frp, daynight`.
Both archive CSVs additionally end with `type`; NRT files lack that column.
Each CSV has zero exact duplicate rows. Every input detection is retained in
raw counts; no confidence/type filtering or spatial de-duplication is applied.

## Product and geographic evidence

MODIS archive rows all identify instrument `MODIS`, satellites Aqua (89,225)
and Terra (27,262), and version `61.03`. Its NRT rows identify instrument
`MODIS`, satellites Aqua (3,947)/Terra (1,578), and version `6.1NRT`.
These contents support MODIS Collection 6.1; NASA's readme independently maps
the M-C61 product code to that collection. The exact meaning of the `.03`
revision suffix was not independently resolved; it is preserved unchanged.

VIIRS archive and NRT rows all identify satellite `SNPP`, instrument `SNPP`,
and versions `2` and `2.0NRT`, respectively. These contents establish S-NPP
Collection 2 rather than relying only on the filenames. NASA's readme maps
SV-C2 downloads to the S-NPP VIIRS 375 m product. This export uses brightness
header aliases; it is not evidence of MODIS instrument identity.

Detection coordinate extents (latitude range; longitude range):

| Source | Latitude | Longitude | Outside supplied Nigeria ADM1 polygon union |
|---|---|---|---:|
| MODIS archive | 4.395–13.8322 | 2.6983–14.6627 | 160 |
| MODIS NRT | 4.39334–13.67042 | 2.75513–14.5906 | 0 |
| S-NPP archive | 4.36874–13.85999 | 2.67916–14.66834 | 1,174 |
| S-NPP NRT | 4.39535–13.69528 | 2.78384–14.60855 | 23 |

The observations are regionally consistent with Nigeria, but exact Nigeria-only
geographic scope and completeness are **not established**. Different boundary
versions or border/coast locations may explain outside points; the request
geography is absent. Coordinate extents above are inventory statistics, not
filtering boxes. All state selection uses the real geoBoundaries Kaduna polygon
from `data/boundaries/nigeria_adm1.geojson`, with point centers on edges included
and hole interiors excluded.

## Matched inputs and actual results

The combined archive/NRT observed ranges overlap from 2024-11-01 to 2026-11-02,
but quality transitions differ between sensors. This first dataset uses **only
standard-quality archives** and their common inclusive interval
**2024-11-01–2026-07-31**. No NRT records are mixed into the output.

Prepared canonical inputs:

| Path | Rows | Preparation |
|---|---:|---|
| `data/raw/modis_c61_nigeria.csv` | 116,346 | MODIS archive clipped to common dates; 141 August detections excluded |
| `data/raw/viirs_snpp_375m_nigeria.csv` | 808,083 | S-NPP archive over the same interval |

The `_nigeria` filenames follow the existing CLI convention, not a claim that
all raw points fall inside Nigeria. Field values are preserved; files are
written with one header. Originals remain intact. `data/raw/provenance.json`
records source/prepared hashes, interval and row counts. Preparation refuses
to overwrite a different existing canonical CSV.

| Sensor | Kaduna detections | Weekly rows | Actual Kaduna detection dates |
|---|---:|---:|---|
| MODIS | 7,875 | 57 | 2024-11-05–2026-05-02 |
| VIIRS_SNPP | 57,241 | 85 | 2024-11-02–2026-07-31 |
| Total | **65,116** | **142** | |

There are 92 ISO weeks intersecting the selected interval. MODIS has no supplied
Kaduna detections in 35 of them; S-NPP has none in 7. Those sensor-week keys
remain absent, not zero-filled. In particular, the lack of MODIS Kaduna rows
after May 2 does not demonstrate zero fires or complete satellite coverage.
The interval's edge weeks, 2024-W44 and 2026-W31, are partial weeks.

## Exploratory paired comparison

There are 581 shared regional detection dates before the state filter and
274 shared Kaduna detection dates. Both sensors have positive Kaduna counts
in **57 common ISO weeks**, across ISO years 2024, 2025 and 2026. This is enough
for the existing descriptive paired-week comparison, not scientific calibration.

Method: inner join on area + ISO year + ISO week, then divide summed VIIRS
raw detections by summed MODIS raw detections for those paired weeks.

Paired totals: **56,952 / 7,875 = 7.232** (VIIRS_SNPP / MODIS).
The remaining 289 VIIRS detections occur in weeks without supplied MODIS
Kaduna detections and do not enter that ratio. No output count is adjusted.

This is not a validated scientific correction. Positive detections do not prove
equal daily coverage; weekly pairing does not match individual fires or
overpasses. Resolution, cloud, confidence, algorithm and overpass differences
confound the ratio. Long MODIS detection gaps and partial edge weeks require
caution. Complete acquisition/coverage metadata, longer matched historical
periods and independent held-out evaluation are needed for calibration.

## Executed validation and artifacts

The existing CLI ran successfully both without and with `--exploratory`.
Independent verification reconstructed counts directly from canonical CSV
coordinates/dates and compared them to the exports. Checks passed for:
nonempty output, exact sensor labels, positive integer counts, unique output
keys, valid ISO weeks, CSV/JSON agreement, original/prepared hashes, and no
invented zero rows. Real dates December 30–31, 2024 and December 29–31, 2025
were checked against their following ISO years. Exploratory totals and ratio
were independently recomputed and matched.

Full pytest suite: **30 passed** (final run 0.75 s). Two synthetic regression
tests address actual discovered ingestion issues: MODIS version `61.03` and
S-NPP archive header/instrument aliases. Point predicates now prepare the
unchanged polygon once for performance; selection logic is unchanged.

Artifacts under `data/processed/`:

- `weekly_fire_counts.csv` (7,013 bytes) and `weekly_fire_counts.json`
  (21,750 bytes), each with 142 rows/objects.
- `manifest.json`: real inputs, hashes, date bounds and counts.
- `exploratory_harmonization.json`: descriptive comparison only.
- `download_audit.json`: complete recursive inventory and daily detection counts.
- `verification.json`: independent verification, missing-week lists and hashes.

Frontend fields remain `area` (string, `Kaduna State`), `year` (integer ISO
year), `week` (integer ISO week), `sensor` (`MODIS` or `VIIRS_SNPP`), `count`
(integer raw detections), `metric` (`raw_detections`). Unique key:
`(area, year, week, sensor, metric)`.

## Reproduce in Windows PowerShell

From the repository root, after the README environment setup:

```powershell
.\.venv\Scripts\python.exe scripts/audit_downloads.py
.\.venv\Scripts\python.exe scripts/prepare_real_inputs.py
.\.venv\Scripts\python.exe -m firelens --area kaduna --exploratory
.\.venv\Scripts\python.exe scripts/verify_real_outputs.py
New-Item -ItemType Directory -Force .pytest-work | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-work/reproduction
```

No blocker remains for using the verified raw weekly dataset in the UI.
Original request/coverage metadata remains needed to establish geographic and
temporal completeness. No additional downloads are necessary for this
exploratory comparison; later standard-quality data is needed before extending
the matched archive interval beyond July 2026. Canonical raw CSVs and generated
outputs remain excluded by the repository's existing `.gitignore`; retain or
transfer these artifacts explicitly when handing the dataset to a teammate.
