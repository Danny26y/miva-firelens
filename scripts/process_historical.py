"""Stream supplied downloads through existing validation/aggregation; no correction.

Requires inventory_historical.py. Originals are referenced, never rewritten.
Standard archive and NRT counts are exported separately.
"""
import csv
import hashlib
import json
import shutil
import sqlite3
import tempfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from itertools import islice
from pathlib import Path

import shapely
from shapely.geometry import shape

from firelens.comparison import compare_weeks
from firelens.pipeline import FIELDS, aggregate, export, fingerprint, iter_csv, kaduna_boundary

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed"


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def snapshot():
    target = ROOT / "data/backups" / ("historical_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ"))
    target.mkdir(parents=True)
    hashes = []
    for name in ("processed", "raw"):
        original = ROOT / "data" / name
        shutil.copytree(original, target / name)
        for path in original.rglob("*"):
            if path.is_file():
                relative = path.relative_to(ROOT / "data")
                expected = fingerprint(path)["sha256"]
                assert fingerprint(target / relative)["sha256"] == expected
                hashes.append({"relative_path": str(relative), "sha256": expected})
    save(target / "backup_hashes.json", hashes)
    return str(target)


def rows_from_counts(counts):
    return [dict(zip(FIELDS, ("Kaduna State", y, w, s, n, "raw_detections")))
            for (y, w, s), n in sorted(counts.items())]


def scan(item, sensor, boundary, nigeria, database):
    path = Path(item["path"])
    assert fingerprint(path)["sha256"] == item["sha256"]
    counts, independent = Counter(), Counter()
    selected_dates, selected_types, selected_versions = Counter(), Counter(), Counter()
    outside_nigeria = selected = total = duplicate_rows = 0
    database.execute("DROP TABLE IF EXISTS seen")
    database.execute("CREATE TABLE seen (digest BLOB PRIMARY KEY) WITHOUT ROWID")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        raw = iter(csv.DictReader(handle))
        observations = iter(iter_csv(path, sensor, allow_legacy_modis=True))
        while True:
            batch = list(islice(observations, 25000))
            if not batch:
                break
            originals = list(islice(raw, len(batch)))
            assert len(originals) == len(batch)
            for row in aggregate(batch, boundary):
                counts[(row["year"], row["week"], sensor)] += row["count"]
            # Separate vectorized predicate/date reconstruction verifies selection
            # and ISO grouping without reusing aggregate's returned values.
            points = shapely.points([float(r["longitude"]) for r in originals],
                                    [float(r["latitude"]) for r in originals])
            mask = shapely.covers(boundary, points)
            outside_nigeria += len(batch) - int(shapely.covers(nigeria, points).sum())
            for row, included in zip(originals, mask):
                if included:
                    d = date.fromisoformat(row["acq_date"])
                    y, w, _ = d.isocalendar()
                    independent[(y, w, sensor)] += 1
                    selected_dates[d.isoformat()] += 1
                    selected_types[row.get("type", "not_supplied")] += 1
                    selected_versions[row["version"]] += 1
            selected += int(mask.sum())
            # Disk-backed SHA-256 full-row identity check, not de-duplication.
            before = database.total_changes
            database.executemany("INSERT OR IGNORE INTO seen VALUES (?)", [
                (hashlib.sha256(json.dumps(list(r.values()), separators=(",", ":")).encode()).digest(),)
                for r in originals])
            duplicate_rows += len(batch) - (database.total_changes - before)
            database.commit()
            total += len(batch)
            if total % 250000 == 0:
                print(f"{path.name}: {total:,} validated; {selected:,} Kaduna", flush=True)
        assert next(raw, None) is None
    assert total == item["rows"]
    assert counts == independent
    assert fingerprint(path)["sha256"] == item["sha256"], "Original changed during processing"
    return counts, {"source": str(path), "sensor": sensor, "validated_rows": total,
                    "kaduna_rows": selected, "kaduna_dates": dict(sorted(selected_dates.items())),
                    "kaduna_versions": dict(selected_versions), "kaduna_types": dict(selected_types),
                    "outside_nigeria_adm1_union": outside_nigeria,
                    "duplicate_full_rows_sha256": duplicate_rows,
                    "duplicates_policy": "count all raw rows; never silently remove duplicates"}


def validate_exports(rows):
    assert rows
    keys = set()
    for r in rows:
        assert list(r) == list(FIELDS)
        assert r["area"] == "Kaduna State" and r["metric"] == "raw_detections"
        assert r["sensor"] in {"MODIS", "VIIRS_SNPP"}
        assert all(type(r[k]) is int for k in ("year", "week", "count")) and r["count"] > 0
        date.fromisocalendar(r["year"], r["week"], 1)
        key = tuple(r[k] for k in ("area", "year", "week", "sensor", "metric"))
        assert key not in keys
        keys.add(key)
    decoded = json.loads((OUT / "weekly_fire_counts.json").read_text())
    with (OUT / "weekly_fire_counts.csv").open(newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    for r in csv_rows:
        for key in ("year", "week", "count"):
            r[key] = int(r[key])
    assert rows == decoded == csv_rows
    assert rows == json.loads((OUT / "historical_calendar.json").read_text())


def main():
    inventory = json.loads((OUT / "historical_inventory.json").read_text())
    backup = snapshot()
    print("Verified backup: " + backup, flush=True)
    boundary_path = ROOT / "data/boundaries/nigeria_adm1.geojson"
    boundary = kaduna_boundary(boundary_path)
    features = json.loads(boundary_path.read_text())["features"]
    nigeria = shapely.union_all([shape(f["geometry"]) for f in features])
    shapely.prepare(boundary)
    shapely.prepare(nigeria)
    all_counts, nrt_counts, quality = Counter(), Counter(), []
    archive_by_sensor = {}
    work = ROOT / ".historical-work"
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work) as temporary:
        connection = sqlite3.connect(str(Path(temporary) / "row_identity.sqlite"))
        # Disposable duplicate-audit index; originals and outputs never depend
        # on SQLite durability. Bound cache memory for large random hash keys.
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA cache_size=-131072")
        try:
            for item in inventory["files"]:
                if "rows" not in item:
                    continue
                instruments = set(item["instruments"])
                if instruments == {"MODIS"} and set(item["satellites"]) <= {"Terra", "Aqua"} and set(item["versions"]) <= {"6.03", "61.03", "6.1NRT"}:
                    sensor = "MODIS"
                elif instruments == {"SNPP"} and set(item["satellites"]) == {"SNPP"} and set(item["versions"]) <= {"2", "2.0NRT"}:
                    sensor = "VIIRS_SNPP"
                else:
                    raise ValueError(f"Unexpected product content: {item['path']}")
                is_nrt = any("NRT" in v for v in item["versions"])
                assert all(("NRT" in v) == is_nrt for v in item["versions"])
                counts, result = scan(item, sensor, boundary, nigeria, connection)
                result["quality"] = "NRT" if is_nrt else "standard_archive"
                quality.append(result)
                if is_nrt:
                    nrt_counts.update(counts)
                else:
                    assert sensor not in archive_by_sensor, "Multiple archive files need explicit overlap review"
                    archive_by_sensor[sensor] = item
                    all_counts.update(counts)
        finally:
            connection.close()
    assert set(archive_by_sensor) == {"MODIS", "VIIRS_SNPP"}
    rows = rows_from_counts(all_counts)
    start = date.fromisoformat(max(f["first_date"] for f in archive_by_sensor.values()))
    end = date.fromisoformat(min(f["last_date"] for f in archive_by_sensor.values()))
    assert start <= end
    comparison = compare_weeks(rows, start, end)
    export(rows, OUT)
    save(OUT / "historical_calendar.json", rows)
    export(rows_from_counts(nrt_counts), OUT / "nrt")
    save(OUT / "historical_comparison.json", comparison)
    save(OUT / "exploratory_harmonization.json", comparison)
    with (OUT / "paired_weeks.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison["pairs"][0]))
        writer.writeheader()
        writer.writerows(comparison["pairs"])
    coverage = {}
    for sensor, item in archive_by_sensor.items():
        first, last = date.fromisoformat(item["first_date"]), date.fromisoformat(item["last_date"])
        opportunities = set()
        d = first
        while d <= last:
            opportunities.add(tuple(d.isocalendar()[:2]))
            d += timedelta(days=1)
        present = {(y, w) for y, w, s in all_counts if s == sensor}
        missing_dates = []
        d = first
        while d <= last:
            if d.isoformat() not in item["dates"]:
                missing_dates.append(d.isoformat())
            d += timedelta(days=1)
        coverage[sensor] = {"observed_bounds": [str(first), str(last)],
                            "weekly_rows": len(present),
                            "kaduna_rows": sum(v for (y, w, s), v in all_counts.items() if s == sensor),
                            "absent_kaduna_weeks_unknown_not_zero": [list(k) for k in sorted(opportunities - present)],
                            "absent_regional_detection_dates_unknown_not_zero": missing_dates}
    validate_exports(rows)
    manifest = {"status": "VERIFIED", "backup": backup, "area": "Kaduna State",
                "metric": "raw_detections", "quality": "standard archives only; NRT exported separately under nrt/",
                "modis_version_warning": "6.03 before 2023 and 61.03 from 2023; not a uniform Collection 6.1 record. No adjustment applied.",
                "sources": [{k: v for k, v in f.items() if k != "dates"} for f in inventory["files"]],
                "boundary": fingerprint(boundary_path), "weekly_output_rows": len(rows),
                "kaduna_observations": sum(r["count"] for r in rows),
                "missing_weeks": "unknown, not zero-filled", "coverage": coverage}
    save(OUT / "manifest.json", manifest)
    save(OUT / "historical_quality.json", quality)
    save(OUT / "download_audit.json", inventory)
    save(ROOT / "data/raw/historical_sources.json", {"sources": [fingerprint(f["path"]) for f in inventory["files"]],
                                                   "policy": "original downloads referenced in place; previous canonical CSVs preserved"})
    save(OUT / "verification.json", {"status": "VERIFIED", "backup": backup,
         "checks": ["complete schema/row validation", "unchanged original hashes", "actual Kaduna polygon",
                    "independent vectorized recount agrees", "unique keys", "ISO dates", "CSV/JSON/calendar agreement", "no zero imputation"],
         "artifacts": [fingerprint(OUT / name) for name in ("weekly_fire_counts.csv", "weekly_fire_counts.json", "historical_calendar.json", "historical_comparison.json")]})
    print(json.dumps({"weekly_rows": len(rows), "kaduna_count": sum(r["count"] for r in rows),
                      "coverage": {s: {k: v for k, v in c.items() if not k.startswith("absent")} for s, c in coverage.items()},
                      "comparison": comparison["overall"]}), flush=True)


if __name__ == "__main__":
    main()
