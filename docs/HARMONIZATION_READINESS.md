# Harmonization readiness — 14 November 2026

**Decision: GO for a qualified raw-data pitch on 15 November; NO-GO for fitting
or applying a scientifically defensible harmonization correction yet.**
The data support descriptive sensor comparisons. They do not establish equal
observational opportunity, interchangeable sensors, or complete fire histories.
No model was trained, tuned or applied in this assessment.

## Evidence versus unresolved interpretation

**Measured:** the supplied MODIS CSV changes from `6.03` through 2022-12-31 to
`61.03` from 2023-01-01. Its 15 columns remain unchanged. Historical standard
exports contain 128,288 MODIS and 443,493 VIIRS S-NPP Kaduna detection rows.
The previous spatial/ISO/export checks passed; this assessment additionally
verified unchanged SHA-256 hashes for 33 protected data, boundary and export files.

**Documented:** the [MCD14ML guide, §§5.5.1–5.5.2](https://lpdaac.usgs.gov/documents/876/MOD14_User_Guide_v6.pdf)
distinguishes collection (`CCC`) from within-collection monthly-product revision
(`VV`, including `03`). Revision 3 retained revision 2's file format while
improving hotspot typing. Thus a format/revision number is not a collection.
[NASA's FIRMS attributes](https://modaps.modaps.eosdis.nasa.gov/services/about/products/c61-nrt/MCD14DL-NRT.html)
describe the version field as collection/source information. These sources
support interpreting the CSV prefixes as collection-related, but do not provide
a verified export-specific mapping for these particular historical rows.

**Inference, not confirmed lineage:** `6.03` and `61.03` are consistent with
different collection identifiers sharing monthly revision 03. Neither identical
columns nor the shared `.03` proves equivalent calibration/algorithms. Conversely,
the label boundary alone does not prove a physical sensor-response break on
January 1. [LAADS's C6 retirement notice](https://ladsweb.modaps.eosdis.nasa.gov/alerts-and-issues/199622)
describes calibration differences and a February 2023 forward-processing change;
it does not establish the January boundary in this CSV. The advertised M-C61
download name is insufficient lineage evidence.

**Required resolution:** obtain original monthly filenames with collection and
revision components, corresponding MOD14/MYD14 granule collection/processing
metadata, or explicit FIRMS/UMD confirmation for request `848634`, especially
December 2022/January 2023. Ask whether older `6.03` rows are legacy C6 or C6.1
records retaining an older export label. The combined 2021 guide returned HTTP
403 during this investigation; no equivalence claim is based on unread text.
This resolves the earlier report's uncertainty about the *role* of `.03`, but
does not certify the actual processing lineage. Existing reports/data are preserved.

## Record availability is not observation exposure

Counts below use each standard CSV's first/last **positive regional detection
dates** as bounds, not as proof of complete requested coverage.

| Sensor / native interval | Calendar weeks | Partial endpoint weeks | Weeks with Kaduna rows | Weeks without Kaduna rows | Kaduna detection dates / days in bounds |
|---|---:|---:|---:|---:|---:|
| MODIS, 2000-11-01–2026-08-31 | 1,349 | 2 | 734 | 615 | 3,439 / 9,435 |
| S-NPP, 2012-01-20–2026-07-31 | 759 | 2 | 603 | 156 | 3,052 / 5,307 |

MODIS endpoint weeks are 2000-W44 (5 in-bound days) and 2026-W36 (1).
S-NPP endpoints are 2012-W03 (3 days) and 2026-W31 (5). These are identifiable
**calendar truncations only**; actual partial swath/cloud coverage is unknown
for every week. Seven dates with detections occurred in 275 MODIS and 291
S-NPP weeks, but even those do not certify seven fully observed days.

Native-period seasonal availability, assigned by ISO Thursday month:

| Sensor | DJF rows-present / eligible weeks | MAM | JJA | SON |
|---|---:|---:|---:|---:|
| MODIS | 335 / 335 | 220 / 342 | 27 / 341 | 152 / 331 |
| S-NPP | 187 / 187 | 193 / 197 | 88 / 193 | 135 / 182 |

These unequal native spans are not a matched sensor-performance experiment.
DJF/MAM/JJA/SON are calendar groupings, not inferred Kaduna wet/dry seasons.
Detailed **ISO-year and year-by-season** counts, endpoint flags and detection-day
activity are in [year availability](../data/readiness/2026-11-14/year_record_availability.csv),
[year-season availability](../data/readiness/2026-11-14/year_season_record_availability.csv)
and [weekly diagnostics](../data/readiness/2026-11-14/weekly_record_availability.csv).

The common observed-date span, 2012-01-20–2026-07-31, contains **757 full
calendar weeks** plus two truncated endpoint weeks. Of those full weeks:
410 have positive rows from both sensors, 191 only S-NPP, six only MODIS, and
150 neither. All unpaired/absent records remain **unknown exposure**, not zero
fires. The old comparison's `partial_edge_weeks=319` also counts observed keys
outside the overlap; it is **not 319 partially observed overlap weeks**.

Regional positive detection dates cover 8,568/9,435 MODIS and 5,201/5,307 S-NPP
days; absent regional-date counts are 867 and 106. These are detection-activity
statistics, **not satellite observation coverage percentages**. NRT remains
separate: MODIS has 5/11 weeks with Kaduna records, S-NPP 14/15, with two
endpoint-truncated weeks per NRT file. None repairs archive exposure uncertainty.

## What exposure information is available?

| Available in these downloads | Missing / external information needed |
|---|---|
| Detected pixel centers, UTC date/time, platform, day/night | All acquired/processed overpasses, including those with no detections |
| Scan/track of detected pixels, confidence, FRP, brightness | Valid observable land area, cloud/unknown/missing-input mask fractions |
| Collection-like version labels; archive `type`; source hashes | Granule IDs, collection lineage, monthly-product revision, reprocessing dates |
| Positive-record dates and weekly counts | Counts of valid non-fire pixels and verified observed-zero detection windows |

Use co-located **MOD14/MYD14 and S-NPP VNP14IMG Level-2 fire masks, QA and
geolocation**, plus granule/processing availability and outage metadata, to
build the denominator. These mask products distinguish valid non-fire,
cloud/unknown and unprocessed conditions; the positive-only FIRMS CSVs do not.
See the [MODIS guide](https://lpdaac.usgs.gov/documents/876/MOD14_User_Guide_v6.pdf)
and [VIIRS C2 guide](https://ladsweb.modaps.eosdis.nasa.gov/archive/Document%20Archive/Science%20Data%20Product%20Documentation/VIIRS_C2_AF-375m_User_Guide_1.2.pdf).
Do not substitute detection counts, detection-day fractions, nominal revisit
frequency, or detected-pixel scan×track sums for exposure. Resolve exposure
separately for Terra, Aqua, S-NPP and day/night before aggregating to a state/week.

## Paired ratios: substantial conditional and seasonal variation

The existing 410 **positive paired full weeks** yield summed VIIRS/MODIS ratio
6.578, weekly median 7.318, Q1–Q3 5.485–11.679 (IQR width 6.194).
Ratios span 0.5–125; 127/410 weeks have MODIS <10, including 44 with MODIS=1.
The <10 exclusion diagnostic leaves 283 pairs: median 6.894 and IQR width
3.112. This sensitivity is evidence against a stable universal weekly ratio,
not justification for discarding low counts from a future calibration.

| ISO-Thursday month | Paired n | Median VIIRS/MODIS | Q1–Q3 | Weeks MODIS <10 |
|---|---:|---:|---|---:|
| Jan | 64 | 6.929 | 6.251–7.970 | 0 |
| Feb | 61 | 8.056 | 7.363–11.132 | 0 |
| Mar | 66 | 13.577 | 8.515–22.979 | 23 |
| Apr | 45 | 17.000 | 8.667–25.750 | 37 |
| May | 21 | 5.250 | 3.000–9.000 | 19 |
| Jun | 10 | 2.800 | 2.000–4.475 | 10 |
| Jul | 3 | 2.000 | 1.571–3.500 | 3 |
| Aug | 3 | 1.000 | 0.750–3.500 | 3 |
| Sep | 5 | 2.000 | 2.000–4.000 | 5 |
| Oct | 14 | 7.125 | 4.250–11.250 | 13 |
| Nov | 57 | 5.500 | 4.504–9.000 | 14 |
| Dec | 61 | 5.518 | 5.199–6.405 | 0 |

Seasonal medians are DJF 6.886 (n=186), MAM 12.905 (132), JJA 2.300 (16),
SON 5.490 (76). All 16 JJA pairs have MODIS <10. Low summer ratios therefore
do not establish reliable summer calibration. Positive-pair conditioning omits
the 347 other full weeks and cannot characterize the observed-zero/missing regime.

Across complete in-bound ISO years 2013–2025, paired n ranges 25–38 and summed
ratios 5.607 (2021)–7.757 (2013). Weekly medians range 6.020 (2020)–8.662 (2018).
Partial 2026 has n=18 and summed ratio 8.913; do not compare it as a full-year
trend. Exact n, quantiles, extremes and low-count frequencies for **every year**
are in [year ratios](../data/readiness/2026-11-14/ratios_by_iso_year.csv), with
[monthly](../data/readiness/2026-11-14/ratios_by_month.csv) and
[seasonal](../data/readiness/2026-11-14/ratios_by_season.csv) equivalents.
Raw Pearson r=0.963 does not remove seasonality, serial dependence or selection
bias and is not validation of interchangeability or causality.

## Candidate method and feasibility — not fitted

**Proposed estimand:** predict VIIRS-equivalent *detection counts* from MODIS,
conditional on measured exposure; neither sensor is ground truth for unique fires.
A simple candidate is a negative-binomial count model with a shared MODIS
response slope and four seasonal intercepts:

`log(mu_V) = log(E_V) + alpha_season + beta * log1p(M / E_M)`.

Here E is valid processed land-area/overpass exposure normalized by the same
Kaduna land area, not a count of detected pixels. Its proportional-offset
assumption, residual overdispersion and season specification would need checking.
Only positive, quality-verified E permits a count label; genuinely observed
zero **detections** may then enter training without claiming zero actual fires.
Leave unobserved windows null. Reconcile collections first; do not absorb an
unverified collection change into an unexplained correction coefficient.

**Untrained holdout audit:** 13 complete in-bound ISO years (2013–2025) permit
13 nominal leave-one-whole-year-out folds, but seven held-out years have no JJA
positive pair. Labels/zeros/exposure are still unresolved, so these are support
counts, not performance scores. Recent label-era complete years are only
2023–2025 (85 pairs):

| Held-out year | Training pairs | Test pairs | Training JJA pairs | Test JJA pairs |
|---|---:|---:|---:|---:|
| 2023 | 57 | 28 | 1 | 0 |
| 2024 | 59 | 26 | 0 | 1 |
| 2025 | 54 | 31 | 1 | 0 |

The 2024 fold cannot estimate a separate JJA effect from positive pairs.
For prospective evaluation, reserve 2025 and train only on 2023–2024; LOYO
folds using later years are retrospective diagnostics. Do not random-split weeks.
Any future preprocessing/tuning must use training years only. Compare against
unadjusted and training-only constant-ratio baselines using held-out count
deviance, MAE, season/low-count errors, annual bias and interval coverage; use
year-block uncertainty. No fitted coefficients, predictions or skill claims exist.

## Limitations and pitch decision

| Limitation | Evidence / assumption status | Consequence / action |
|---|---|---|
| Exposure missing | Measured CSV schema has positive detections only | Blocks scientifically defensible calibration; acquire masks/QA and availability ledger |
| MODIS lineage | Measured label boundary; actual source equivalence unresolved | No collection-equivalence claim; obtain monthly/granule provenance |
| Positive-pair bias | 410/757 full weeks enter current ratios | Report conditional distributions; never fill the remainder with zeros |
| Sparse seasonal support | JJA n=16, all MODIS <10; recent training fold has JJA n=0 | No all-season validation claim; collect verified windows before fitting |
| Thermal-source labels | 460 MODIS type-2; S-NPP 1,255 type-2 and 77 type-3 within Kaduna | Raw counts are not vegetation-fire incident counts; audit inland type-3 records |
| VIIRS `type` revision uncertainty | NASA documents a monthly-product bug; CSV Collection 2 does not identify monthly revision | Verify corrected monthly revision before type-based filtering; do not assert these rows are affected |
| Sensors and platforms differ | Terra+Aqua pooled versus S-NPP, different pixel sizes/timing | Define a conditional count target; keep platform/exposure strata |
| Geographic/temporal completeness | Request polygon and coverage manifest absent | State-bounded detected centers are verified; full fire history is not |

NASA's [VIIRS guide §6.1](https://ladsweb.modaps.eosdis.nasa.gov/archive/Document%20Archive/Science%20Data%20Product%20Documentation/VIIRS_C2_AF-375m_User_Guide_1.2.pdf)
documents type misclassification in monthly revisions 1/2 and correction in
revision 3. Collection 2 (`version=2` here) is a different identifier, so the
bug's applicability to these CSVs remains unverified. No type-based filtering
or change to existing raw counts was made.

**Pitch GO, with conditions:** present the verified weekly thermal-detection
calendar and separate raw sensor comparison. Keep missing weeks gray/unknown,
show sensor and period, mark endpoint truncation and the unresolved version-label
boundary, and state that raw count differences are not fire-growth estimates.
Retain positive-pair n and log-axis labels on ratio/scatter charts. Do not
invent daily counts from ISO-week totals, merge the sensors into a homogeneous
25-year series, call counts incidents/burned area, or show corrected values.

## Next implementation step and reproducibility

Implement an **exposure/provenance ledger first**, not calibration: one row per
platform/day or granule with source collection/revision, QA/availability status,
valid land-area looks, unknown/cloud area, and explicit exclusion reason.
Validate a representative Kaduna pilot window spanning DJF/JJA and the
2022/2023 transition, including no-detection windows; expand only after the
denominator and lineage are verified. Retrieve actual granules/metadata through
NASA access services; none were downloaded or inferred in this assessment.
Acceptance: distinguish a processed no-detection window from unobserved input,
reconcile footprint sums and collection IDs, and leave unknown exposure null.
Then reassess year/season support before any training authorization.

All diagnostics are new under `data/readiness/2026-11-14/`; raw files, earlier
reports and `data/processed/` are unchanged. The new diagnostic module/script
were tested: **39 tests passed** (2.59 s), including three new synthetic checks.
No historical processing or correction was rerun. Reproduce into a **new** folder:

```powershell
.\.venv\Scripts\python.exe scripts/assess_readiness.py --output-dir data/readiness/recheck-01
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-work/readiness-recheck
```

The assessment refuses to overwrite an existing nonempty output directory.
`preservation_hashes.json` records the 33 unchanged protected files;
`readiness_diagnostics.json` contains all counts and untrained holdout plans.
