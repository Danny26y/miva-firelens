# Miva FireLens data pipeline

Minimal offline processor for NASA FIRMS MODIS Collection 6.1 and VIIRS
Suomi-NPP 375 m active-fire CSVs. No frontend, service, ML, or API key required.
The initial repository was empty; no existing teammate files were replaced.

Historical processing uses the replacement downloads directly. See
[the historical report](docs/HISTORICAL_DATA_REPORT.md) for current coverage,
provenance, raw sensor comparisons and limitations. The earlier 142-row dataset
and its canonical input CSVs are preserved in versioned backups;
[its report](docs/REAL_DATA_REPORT.md) describes that earlier snapshot.
Synthetic observations remain confined to tests.

## Current historical workflow (Windows PowerShell)

After environment setup, run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[test,analysis]'
.\.venv\Scripts\python.exe scripts/inventory_historical.py
.\.venv\Scripts\python.exe scripts/process_historical.py
.\.venv\Scripts\python.exe scripts/chart_historical.py
.\.venv\Scripts\python.exe scripts/verify_historical_artifacts.py
.\.venv\Scripts\python.exe scripts/write_historical_report.py
```

Processing makes a hash-verified versioned backup before replacing outputs.
Main exports and `historical_calendar.json` contain standard-archive raw counts;
NRT counts are separate under `data/processed/nrt/`. Historical MODIS includes
legacy version 6.03 and version 61.03; it is not a uniform Collection 6.1 series.
No correction is fitted or applied. Absent observations remain unknown.
The original two-input CLI below still uses the preserved Prompt 2 canonical
CSVs by default; it does **not** discover the replacement historical archives.
Use the historical workflow above to regenerate the current historical files.

## Windows PowerShell: setup and run

Run from the repository root, with Python 3.10+ installed:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[test]'
New-Item -ItemType Directory -Force .pytest-work | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-work/run
```

If using uv instead of the Windows Python launcher:

```powershell
uv --cache-dir .uv-cache venv --python 3.12
uv --cache-dir .uv-cache pip install --python .venv\Scripts\python.exe -e '.[test]'
```

Acquire real CSVs using [the acquisition guide](docs/ACQUISITION.md), saving:

```text
data/raw/modis_c61_nigeria.csv
data/raw/viirs_snpp_375m_nigeria.csv
```

```powershell
# All supplied observations; area is conservatively labeled input_extent.
.\.venv\Scripts\python.exe -m firelens
# Kaduna only, using the included actual Nigeria ADM1 state polygons.
.\.venv\Scripts\python.exe -m firelens --area kaduna
# Optional exploratory comparison (does not alter weekly counts).
.\.venv\Scripts\python.exe -m firelens --area kaduna --exploratory
# Installed console command is equivalent:
.\.venv\Scripts\firelens.exe --area kaduna
```

Custom inputs: `--modis PATH --viirs PATH --boundary PATH --output-dir PATH`.
Both products are required by the CLI to make a comparable UI dataset. Ingestion
functions can be used individually. Missing files or invalid data return exit
code 2 with a useful error; successful runs return 0. Failed validation does not
refresh exports: check exit code and manifest before serving previously created
files. Do not point production commands at test fixtures.

## Frontend contract

Outputs: `data/processed/weekly_fire_counts.csv` and
`data/processed/weekly_fire_counts.json` (JSON array of objects).

| Field | JSON type | Meaning |
|---|---|---|
| area | string | `Kaduna State` only after polygon filtering; otherwise `input_extent` |
| year | integer | ISO week year, not necessarily acquisition calendar year |
| week | integer | ISO week 1–53, Monday start, acquisition date in UTC |
| sensor | string | `MODIS` (Terra + Aqua) or `VIIRS_SNPP` |
| count | integer | Nonnegative number of input detection rows in that group |
| metric | string | `raw_detections` |

Unique key: `(area, year, week, sensor, metric)`. Deterministic sorting by
year, week, sensor. CSV uses the same fields/order; parse integers explicitly.
The verified CSV/JSON files are available under `data/processed`.

`manifest.json` records input paths/SHA-256 hashes, area, counts, and status.
`READY` means processing succeeded, **not** that satellite coverage is complete
or science quality has been independently assessed. No selected points yields
header-only CSV, `[]` JSON and `NO_DETECTIONS_IN_SELECTION`.

Absent weeks/sensors are **unknown**, never automatically zero-filled. The UI
must display a gap rather than infer no fires. Files contain detections, not
unique fire events, burned area, or incident severity. Repeat detections and
duplicate rows remain counted. Do not concatenate overlapping downloads without
auditing duplicates. No confidence threshold is applied. No spatially aggregated
or corrected metric is computed or substituted for raw counts.

## Validation and limitations

Required common columns: `latitude, longitude, scan, track, acq_date, acq_time,
satellite, instrument, confidence, version, frp, daynight`. MODIS additionally
requires `brightness, bright_t31`; VIIRS accepts `bright_ti4, bright_ti5` or
the historical download aliases `brightness, bright_t31`, with `VIIRS` or
`SNPP` as its instrument label and a separately validated S-NPP satellite.
Extra NASA columns are allowed. UTF-8 BOM accepted. Headers are exact/case
sensitive. Missing values, malformed rows, nonfinite/out-of-range coordinates,
wrong platform/instrument, invalid date/time and invalid confidence fail with
filename and row number. MODIS Collection 6.1 is enforced, including the observed
standard archive version spelling `61.03`. Retain the VIIRS
collection/version in acquisition provenance; the product is S-NPP, not NOAA-20.
Dates accept `YYYY-MM-DD`, `YYYY/MM/DD`, and ISO timestamps with no offset or
UTC offset. Ambiguous day/month formats and non-UTC offsets are rejected.

Kaduna filtering uses Shapely point-in-polygon on WGS84 longitude/latitude,
including boundary edges and excluding polygon-hole interiors. This tests the
detection center, not its whole pixel footprint. Boundary loader requires a
valid named Kaduna Polygon/MultiPolygon; source authenticity comes from the
documented provenance, not from the feature name alone.

The exploratory module pairs **area + ISO year + ISO week** present for both
sensors during overlapping ISO years, then reports a ratio of summed paired
counts. Missing weeks are excluded, not imputed. This assumes equal area,
temporal coverage and processing quality; positive observations alone do not
verify those assumptions. Pairing is at weekly level, not individual fire or
overpass level. Resolution, cloud, revisit timing, confidence and algorithm
differences confound results. The ratio is **not a validated scientific
correction**, has no calibrated uncertainty, and never modifies UI counts.
Use independently verified coverage and held-out evaluation before considering
any scientific harmonization. Optional results are written separately to
`exploratory_harmonization.json`; they are descriptive diagnostics only.

Tests cover both schemas, invalid/missing inputs, dates, ISO year transitions,
raw duplicate preservation, sensor separation, polygon edges/holes, CSV/JSON
export, CLI failure/success, and paired-week diagnostics. All fixtures and test
polygons are explicitly synthetic. The real boundary has a separate integration
test; no synthetic data is written to `data/processed` by the tests.
