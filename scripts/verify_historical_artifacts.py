"""Verify completed historical artifacts and snapshots without imputing data."""
import csv
import json
from datetime import date, timedelta
from pathlib import Path

from firelens.comparison import compare_weeks
from firelens.pipeline import FIELDS, fingerprint

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed"


def read(path):
    return json.loads(path.read_text())


def verify_rows(directory):
    rows = read(directory / "weekly_fire_counts.json")
    assert rows
    with (directory / "weekly_fire_counts.csv").open(newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    for row in csv_rows:
        for key in ("year", "week", "count"):
            row[key] = int(row[key])
    assert csv_rows == rows
    keys = set()
    for row in rows:
        assert list(row) == list(FIELDS)
        assert row["area"] == "Kaduna State" and row["metric"] == "raw_detections"
        assert row["sensor"] in {"MODIS", "VIIRS_SNPP"}
        assert all(type(row[k]) is int for k in ("year", "week", "count")) and row["count"] > 0
        date.fromisocalendar(row["year"], row["week"], 1)
        key = tuple(row[k] for k in ("area", "year", "week", "sensor", "metric"))
        assert key not in keys
        keys.add(key)
    return rows


def main():
    manifest = read(OUT / "manifest.json")
    inventory = read(OUT / "historical_inventory.json")
    for item in inventory["files"]:
        assert fingerprint(item["path"])["sha256"] == item["sha256"]
    backup = Path(manifest["backup"])
    for item in read(backup / "backup_hashes.json"):
        assert fingerprint(backup / item["relative_path"])["sha256"] == item["sha256"]
    rows, nrt = verify_rows(OUT), verify_rows(OUT / "nrt")
    assert rows == read(OUT / "historical_calendar.json")
    assert len(rows) == manifest["weekly_output_rows"]
    assert sum(r["count"] for r in rows) == manifest["kaduna_observations"]
    for sensor, coverage in manifest["coverage"].items():
        present = {(r["year"], r["week"]) for r in rows if r["sensor"] == sensor}
        missing = {tuple(k) for k in coverage["absent_kaduna_weeks_unknown_not_zero"]}
        assert not present & missing
        assert sum(r["count"] for r in rows if r["sensor"] == sensor) == coverage["kaduna_rows"]
    comparison = read(OUT / "historical_comparison.json")
    start, end = map(date.fromisoformat, comparison["overlap_date_bounds"])
    assert comparison == compare_weeks(rows, start, end)
    assert comparison == read(OUT / "exploratory_harmonization.json")
    for p in comparison["pairs"]:
        monday = date.fromisoformat(p["monday"])
        assert start <= monday and monday + timedelta(days=6) <= end
        assert p["MODIS"] > 0 and p["VIIRS_SNPP"] > 0
    for name in ("raw_weekly_counts", "raw_paired_scatter", "raw_ratio_by_month"):
        for extension in ("png", "svg"):
            assert (OUT / "charts" / f"{name}.{extension}").stat().st_size > 0
    report = read(OUT / "verification.json")
    report["final_artifact_checks"] = ["original source hashes unchanged", "versioned backup hashes match",
        "standard and NRT exports valid and separated", "CSV/JSON/calendar equality",
        "no duplicate keys", "no absent-week zero imputation", "paired summaries exactly recomputed",
        "paired weeks inside common full-week bounds", "six nonempty chart files"]
    report["artifacts"] = [fingerprint(path) for path in sorted(OUT.rglob("*"))
                           if path.is_file() and path.name not in {"verification.json", ".gitkeep"}]
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": "VERIFIED", "standard_weekly_rows": len(rows),
                      "nrt_weekly_rows": len(nrt), "paired_weeks": comparison["overall"]["n"],
                      "original_files_unchanged": len(inventory["files"])}))


if __name__ == "__main__":
    main()
