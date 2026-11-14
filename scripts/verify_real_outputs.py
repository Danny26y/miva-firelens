"""Independent real-data export verification; no imputation or correction."""
import csv
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import shapely

from firelens.pipeline import fingerprint, kaduna_boundary


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "data/processed"
    provenance = json.loads((root / "data/raw/provenance.json").read_text())
    audit = json.loads((output / "download_audit.json").read_text())
    for original in audit["files"]:
        assert fingerprint(original["path"])["sha256"] == original["sha256"], "Original changed"
    boundary = kaduna_boundary(root / "data/boundaries/nigeria_adm1.geojson")
    shapely.prepare(boundary)
    start, end = date.fromisoformat(provenance["start"]), date.fromisoformat(provenance["end"])
    interval_weeks = set()
    day = start
    while day <= end:
        interval_weeks.add(tuple(day.isocalendar()[:2]))
        day += timedelta(days=1)
    expected, summaries, days_by_sensor = Counter(), {}, {}
    for item in provenance["inputs"]:
        path, sensor = Path(item["prepared"]["path"]), item["sensor"]
        assert fingerprint(path)["sha256"] == item["prepared"]["sha256"]
        dates, lats, lons = [], [], []
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                d = date.fromisoformat(row["acq_date"])
                assert start <= d <= end
                dates.append(d)
                lats.append(float(row["latitude"]))
                lons.append(float(row["longitude"]))
        mask = shapely.covers(boundary, shapely.points(lons, lats))
        selected_dates = [d for d, included in zip(dates, mask) if included]
        days_by_sensor[sensor] = set(selected_dates)
        for d in selected_dates:
            year, week, _ = d.isocalendar()
            expected[("Kaduna State", year, week, sensor, "raw_detections")] += 1
        present = {tuple(d.isocalendar()[:2]) for d in selected_dates}
        summaries[sensor] = {"input_rows": len(dates), "kaduna_rows": len(selected_dates),
                             "kaduna_first_detection": min(selected_dates).isoformat(),
                             "kaduna_last_detection": max(selected_dates).isoformat(),
                             "kaduna_distinct_detection_dates": len(set(selected_dates)),
                             "weekly_rows": len(present),
                             "absent_weeks_unknown_not_zero": [list(w) for w in sorted(interval_weeks - present)]}
    rows = json.loads((output / "weekly_fire_counts.json").read_text())
    assert rows
    actual = {}
    for row in rows:
        assert list(row) == ["area", "year", "week", "sensor", "count", "metric"]
        assert type(row["year"]) is type(row["week"]) is type(row["count"]) is int
        date.fromisocalendar(row["year"], row["week"], 1)
        assert row["count"] > 0
        key = tuple(row[k] for k in ("area", "year", "week", "sensor", "metric"))
        assert key not in actual, "Duplicate output key"
        actual[key] = row["count"]
    assert actual == dict(expected), "Independent counts differ"
    with (output / "weekly_fire_counts.csv").open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    for row in csv_rows:
        for key in ("year", "week", "count"):
            row[key] = int(row[key])
    assert csv_rows == rows
    # Explicit check of calendar-year/ISO-year divergence using actual input dates.
    iso_boundary_dates = {sensor: sorted(d.isoformat() for d in ds if d.year != d.isocalendar().year)
                          for sensor, ds in days_by_sensor.items()}
    shared = days_by_sensor["MODIS"] & days_by_sensor["VIIRS_SNPP"]
    paired_weeks = {tuple(d.isocalendar()[:2]) for d in days_by_sensor["MODIS"]} & {
        tuple(d.isocalendar()[:2]) for d in days_by_sensor["VIIRS_SNPP"]}
    report = {"status": "VERIFIED", "interval": [str(start), str(end)],
              "weekly_output_rows": len(rows), "sensors": summaries,
              "shared_kaduna_detection_dates": len(shared),
              "paired_weeks": len(paired_weeks),
              "actual_iso_year_boundary_dates": iso_boundary_dates,
              "partial_edge_weeks": [list(start.isocalendar()[:2]), list(end.isocalendar()[:2])],
              "checks": ["original hashes unchanged", "independent polygon/date counts equal export", "CSV equals JSON", "unique keys", "positive integer counts", "valid ISO weeks", "no absent-week zero rows"],
              "coverage_limitation": "Matching observed ranges and positive paired weeks do not establish complete overpass/clear-sky coverage or exact original request geography."}
    exploratory = output / "exploratory_harmonization.json"
    if exploratory.exists():
        comparison = json.loads(exploratory.read_text())
        totals = {sensor: sum(n for (_, y, w, s, _), n in expected.items()
                              if s == sensor and (y, w) in paired_weeks)
                  for sensor in ("MODIS", "VIIRS_SNPP")}
        assert comparison["paired_weeks"] == len(paired_weeks)
        assert comparison["modis_total"] == totals["MODIS"]
        assert comparison["viirs_snpp_total"] == totals["VIIRS_SNPP"]
        assert comparison["viirs_to_modis_ratio"] == totals["VIIRS_SNPP"] / totals["MODIS"]
        report["exploratory"] = comparison
    report["export_hashes"] = [fingerprint(output / filename) for filename in
                               ("weekly_fire_counts.csv", "weekly_fire_counts.json", "manifest.json")]
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
