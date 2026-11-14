"""Build a report from executed historical results, never placeholder counts."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed"


def read(name):
    return json.loads((OUT / name).read_text())


def number(value):
    if value is None:
        return "undefined (no valid pairs)"
    return f"{value:,.3f}" if isinstance(value, float) else f"{value:,}"


def main():
    manifest, comparison, quality, inventory = [read(n) for n in (
        "manifest.json", "historical_comparison.json", "historical_quality.json", "historical_inventory.json")]
    verification = read("verification.json")
    tests = read("test_results.json")
    assert manifest["status"] == verification["status"] == "VERIFIED"
    files = [f for f in inventory["files"] if "rows" in f]
    overall = comparison["overall"]
    seasonal_medians = [s["weekly_ratio_median"] for s in comparison["by_season"].values() if s["n"]]
    small_denominator_weeks = overall["n"] - comparison["modis_at_least_10_sensitivity"]["n"]
    inventory_table = "\n".join(
        f"| `{Path(f['path']).relative_to(ROOT).as_posix()}` | {f['bytes']:,} | {f['rows']:,} | {f['first_date']}–{f['last_date']} | `{f['versions']}` |"
        for f in files)
    quality_table = "\n".join(
        f"| {q['sensor']} / {q['quality']} | {q['kaduna_rows']:,} | {min(q['kaduna_dates'])}–{max(q['kaduna_dates'])} | {q['duplicate_full_rows_sha256']:,} | {q['outside_nigeria_adm1_union']:,} | `{q['kaduna_types']}` |"
        for q in quality)
    coverage_table = "\n".join(
        f"| {s} | {'–'.join(c['observed_bounds'])} | {c['kaduna_rows']:,} | {c['weekly_rows']:,} | {len(c['absent_kaduna_weeks_unknown_not_zero']):,} | {len(c['absent_regional_detection_dates_unknown_not_zero']):,} |"
        for s, c in manifest["coverage"].items())

    def stats_table(mapping):
        return "\n".join(f"| {label} | {n['n']} | {number(n['summed_count_ratio'])} | {number(n['weekly_ratio_median'])} | {number(n['weekly_ratio_q1'])}–{number(n['weekly_ratio_q3'])} | {number(n['weekly_ratio_iqr'])} |"
                         for label, n in mapping.items())

    report = f"""# Historical Kaduna data and raw sensor comparison

Run date: 2026-11-14. **VERIFIED** against the supplied observations and the
existing geoBoundaries Kaduna polygon. No harmonization model was fitted and
no correction was applied. Counts are raw thermal detections, not unique fires.

## Preserved state and original inventory

Prompt 2 raw inputs and exports were preserved first at
`data/backups/prompt2_20261114_181403/`, with SHA-256 records. The completed
historical processing run also created and hash-verified this snapshot before
replacing existing outputs: `{manifest['backup']}`. Earlier processed data and
the original canonical raw CSVs remain recoverable. Original NASA downloads
are referenced in place and their SHA-256 hashes were checked before and after
processing. No original was rewritten. An initial slow run was stopped before
export; only the completed, tested batch run produced the current dataset.

Recursive inventory (all six files are recorded in `historical_inventory.json`):

| Original CSV | Bytes | Rows | Actual regional detection dates | Version values and row counts |
|---|---:|---:|---|---|
{inventory_table}

Each download folder also contains an 89-byte `Readme.txt`, linking to
[NASA FIRMS's official download readme](https://firms.modaps.eosdis.nasa.gov/download/Readme.txt).
No request polygon, email or complete coverage metadata is supplied. The
observations do not prove that every requested date or the intended geography
was completely covered.

All CSVs have `latitude, longitude, brightness, scan, track, acq_date, acq_time,
satellite, instrument, confidence, version, bright_t31, frp, daynight` in that
order. Archives additionally have `type`; NRT files do not. Full version,
satellite, instrument, type and coordinate-extent distributions are recorded
per file in `historical_inventory.json`.

## Product identity and nonuniform MODIS version history

MODIS rows identify instrument MODIS and Terra/Aqua platforms. Importantly,
the archive uses **6.03 during 2000-11-01–2022-12-31**, then **61.03 during
2023-01-01–2026-08-31**. The NRT file uses 6.1NRT. Despite the M-C61 directory
name, the archive must not be described as a uniformly labeled Collection 6.1
record. The earlier 6.03 label is treated as a legacy version, with explicit
opt-in to ingestion. Its exact revision suffix has not been independently
resolved. NASA distinguishes [Collection 6 and Collection 6.1](https://atmosphere-imager.gsfc.nasa.gov/collections/overview);
cross-era differences must be treated as a possible confounder, not corrected
by renaming the values. Request collection-consistent reprocessed records or
NASA confirmation before attributing cross-era changes scientifically.

VIIRS rows identify both satellite and instrument as SNPP and version 2
(standard) or 2.0NRT. Combined with NASA's SV-C2 product documentation, these
contents identify S-NPP VIIRS 375 m Collection 2 rather than relying solely
on the folder name. This historical export uses brightness column aliases;
they do not imply a MODIS instrument. VIIRS starts in January 2012, so there
are not 25 years of VIIRS observations in these downloads.

## Processing, geography, duplication and missing data

The existing validator now exposes an incremental iterator while preserving
the list-returning API. Bounded batches use the same Shapely `covers` predicate
against the unchanged actual Kaduna Polygon/MultiPolygon. The scalar-point
implementation was replaced by its batch equivalent for throughput; polygon
edges remain included and hole interiors excluded. UTC HHMM validation uses
equivalent integer hour/minute bounds. Existing tests and new regression tests
cover these changes.

Every row is validated. An independent vectorized coordinate/date recount
agrees with the existing aggregation code. A temporary disk-backed SQLite
index of SHA-256 full-row identities checks duplicates without holding
millions of rows in memory. All duplicates, if any, remain in raw counts;
none are silently removed. Canonical raw CSVs from Prompt 2 are preserved;
`data/raw/historical_sources.json` references the current original downloads.

| Product / quality | Kaduna detections | Actual Kaduna detection dates | Duplicate full rows | Regional points outside Nigeria ADM1 union | Kaduna type counts |
|---|---:|---|---:|---:|---|
{quality_table}

Coordinate extents are inventory measurements, never filtering boxes. Some
regional points may fall outside the supplied Nigeria union; geographic scope
and boundary alignment are not assumed. The real state polygon alone decides
Kaduna selection. No confidence or `type` threshold is applied: these are all
raw detections, potentially including non-vegetation thermal sources. The type
counts above must be reviewed before interpreting the counts as vegetation fires.

The primary dataset keeps each sensor's full standard-archive history. NRT is
exported separately under `data/processed/nrt/`; it is never mixed with the
standard observations in comparisons or the historical calendar.

| Sensor | Regional observed date bounds | Kaduna detections | Weekly output rows | Absent Kaduna sensor-weeks | Absent regional detection dates |
|---|---|---:|---:|---:|---:|
{coverage_table}

Primary total: **{manifest['kaduna_observations']:,} detections in
{manifest['weekly_output_rows']:,} weekly sensor rows**. Absent weeks/dates are
**unknown, not zero detections**. `manifest.json` lists them explicitly.
Rows only exist for positive supplied counts. Weeks before VIIRS availability
must remain unavailable, not zero. Boundary years and partial endpoint weeks
are incomplete, so full-year totals must not be assumed comparable. NASA also
documents historical MODIS omissions in its download readme; a detection CSV
alone cannot distinguish a fire-free day from missing/cloud-obscured coverage.

## Verified paired-week relationship (descriptive only)

Common standard regional observation-date bounds:
**{'–'.join(comparison['overlap_date_bounds'])}**. Comparison includes only ISO
weeks fully within these bounds and with positive supplied observations from
both sensors. A full calendar week inside the bounds does **not** prove full
satellite coverage. No absent sensor is imputed. Full ISO weeks avoid mismatching
partially observed edge weeks between sensors. Exclusions among observed week
keys: `{comparison['excluded_observed_week_keys']}`. Pre-overlap/post-overlap
weeks are also outside the bounds and included in that edge/bounds exclusion tally.

- Paired sample size: **{overall['n']} weeks**.
- Paired raw totals: MODIS **{overall['modis_total']:,}**, VIIRS S-NPP
  **{overall['viirs_snpp_total']:,}**.
- Summed-count ratio, VIIRS/MODIS: **{number(overall['summed_count_ratio'])}**.
- Median weekly ratio: **{number(overall['weekly_ratio_median'])}**.
- Weekly ratio Q1–Q3: **{number(overall['weekly_ratio_q1'])}–{number(overall['weekly_ratio_q3'])}**;
  IQR width **{number(overall['weekly_ratio_iqr'])}**.
- Descriptive raw-count Pearson r: **{number(overall.get('raw_pearson_r'))}**;
  log1p-count Pearson r: **{number(overall.get('log1p_pearson_r'))}**.

Quartiles use linear interpolation at `(n-1)*p`; the summed-count ratio is
not the median of weekly ratios. Division by zero is excluded explicitly;
undefined summaries are null. Positive-pair selection still creates selection
bias and ratios with tiny positive MODIS denominators can be unstable.

Sensitivity analysis requiring MODIS count >=10:
`{comparison['modis_at_least_10_sensitivity']}`.
This is a denominator-stability diagnostic, not a justified filtering rule
for calibration or production raw counts.

Calendar seasons below are DJF, MAM, JJA and SON, assigned by the month of ISO
Thursday. They are descriptive month groups, not a claim about local wet/dry
season boundaries. Unequal samples and unobserved weeks prevent treating them
as an unbiased seasonal response estimate.

| Season | Paired n | Summed ratio | Weekly median | Q1–Q3 | IQR width |
|---|---:|---:|---:|---|---:|
{stats_table(comparison['by_season'])}

| MODIS version-label era | Paired n | Summed ratio | Weekly median | Q1–Q3 | IQR width |
|---|---:|---:|---:|---|---:|
{stats_table(comparison['by_modis_version_era'])}

Transition weeks are identified separately rather than assigned to a uniform
version era. Monthly summaries, all paired records and exact numerical values
are available in `historical_comparison.json` and `paired_weeks.csv`. The overall
ratio must not be presented as an invariant conversion across seasons or eras.
Correlation is descriptive and can be driven by shared seasonality and serial
dependence; it does not validate sensor interchangeability.

Observed seasonal median ratios span **{number(min(seasonal_medians))} to
{number(max(seasonal_medians))}**. **{small_denominator_weeks} paired weeks**
have MODIS counts below 10. These observed distribution and denominator
differences motivate stratified evaluation rather than choosing one global
scaling factor; they do not by themselves identify a causal sensor bias.

## Charts, calendar export and verification

![Raw weekly detections](../data/processed/charts/raw_weekly_counts.png)

![Raw paired counts](../data/processed/charts/raw_paired_scatter.png)

![Raw ratios by calendar month](../data/processed/charts/raw_ratio_by_month.png)

Each chart is available as PNG and SVG. Time-series gaps are NaN/absent points,
never fabricated zeros. Scatter reference lines indicate equal counts, not a
fitted correction. Log scales are labeled. Ratio figures show raw unadjusted
ratios, including their outliers.

Primary artifacts in `data/processed/`:

- `weekly_fire_counts.csv`, `weekly_fire_counts.json`: complete native-period
  standard-archive weekly counts.
- `historical_calendar.json`: the same JSON array of records, with exactly
  `area, year, week, sensor, count, metric` for the existing frontend.
- `manifest.json`, `historical_inventory.json`, `historical_quality.json`,
  `verification.json`: coverage, original hashes, row validation, duplication,
  geographic selection and independent export agreement.
- `historical_comparison.json`, `paired_weeks.csv`, and
  `exploratory_harmonization.json`: descriptive statistics only. The latter
  replaces the old Prompt 2 diagnostic, which is preserved in backups.
- `nrt/weekly_fire_counts.csv` and `.json`: separate NRT raw counts.
- `charts/raw_weekly_counts`, `raw_paired_scatter`, `raw_ratio_by_month`:
  PNG/SVG comparison charts.

Frontend contract is unchanged: `area` string (`Kaduna State`), `year` integer
ISO week year, `week` integer ISO week 1–53, `sensor` string (`MODIS` or
`VIIRS_SNPP`), `count` positive integer detection rows, `metric` string
`raw_detections`. Unique key is `(area, year, week, sensor, metric)`.
This is calendar-ready weekly data; it must not be expanded into invented
daily counts. No absent week is turned into a zero-valued record.

The completed export verification confirms schema, positive counts, real
polygon selection, unique keys, valid ISO weeks, CSV/JSON/calendar equality,
unchanged original hashes and independent per-week recount agreement.
The final pytest run passed **{tests['passed']} tests** in
{tests['elapsed_seconds']} seconds, with its exact executed command recorded
in `test_results.json`. All fixtures remain synthetic and test-only.

## Reproduction in Windows PowerShell

From `C:\\Users\\Daniel\\Desktop\\miva-firelens`, with the current original
downloads in place:

```powershell
.\\.venv\\Scripts\\python.exe -m pip install -e '.[test,analysis]'
.\\.venv\\Scripts\\python.exe scripts/inventory_historical.py
.\\.venv\\Scripts\\python.exe scripts/process_historical.py
.\\.venv\\Scripts\\python.exe scripts/chart_historical.py
.\\.venv\\Scripts\\python.exe scripts/verify_historical_artifacts.py
.\\.venv\\Scripts\\python.exe scripts/write_historical_report.py
New-Item -ItemType Directory -Force .pytest-work | Out-Null
.\\.venv\\Scripts\\python.exe -m pytest -q --basetemp=.pytest-work/historical-reproduction
```

`process_historical.py` takes a new versioned, hash-verified backup before
replacing processed files. It references the historical sources directly;
the older default CLI inputs remain the preserved Prompt 2 files. Use the
historical command above to reproduce this dataset. Output/backup directories
are gitignored; transfer or preserve them explicitly for handoff.

## Limitations and recommended next method

No blocker remains to exploring the supplied raw weekly dataset. Scientific
interpretation is limited by incomplete exposure/coverage metadata, the MODIS
version change, confidence/type mixtures, platform/overpass differences, cloud,
resolution and unmatched weeks. The supplied archive ends differ between
sensors. Historical absence is not evidence of fire absence. The source
readmes do not certify a complete Nigeria request.

Next, obtain collection-consistent MODIS observations and valid-observation
exposure/coverage metadata for both sensors; review the non-vegetation type
policy. Then compare the raw paired distributions by season, version era and
coverage. If a correction is later justified, evaluate a count regression
allowing overdispersion (for example negative binomial), season/era effects
and measured exposure offsets, using held-out whole years and year-block
resampling for uncertainty. Compare it to an unadjusted baseline and test
sensitivity to positive-pair selection and low counts. It should be a predictive
relationship with stated uncertainty, not a declaration that VIIRS is ground
truth or a scientific correction validated by a simple ratio. **No such model
has been fitted or applied here.**
"""
    (ROOT / "docs/HISTORICAL_DATA_REPORT.md").write_text(report, encoding="utf-8")
    print("Wrote docs/HISTORICAL_DATA_REPORT.md")


if __name__ == "__main__":
    main()
