"""Inventory real NASA downloads without changing them or production outputs."""
import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path

import shapely
from shapely.geometry import shape

from firelens.pipeline import fingerprint, kaduna_boundary


def main():
    root = Path(__file__).resolve().parents[1]
    boundary_path = root / "data/boundaries/nigeria_adm1.geojson"
    kaduna = kaduna_boundary(boundary_path)
    features = json.loads(boundary_path.read_text())["features"]
    nigeria = shapely.union_all([shape(f["geometry"]) for f in features])
    shapely.prepare(kaduna)
    shapely.prepare(nigeria)
    report = {"files": [], "coverage_caveat": "Detection extents and dates do not prove requested geographic scope or complete satellite coverage."}
    for folder in ("DL_FIRE_M-C61_848524", "DL_FIRE_SV-C2_848525"):
        for path in sorted((root / folder).rglob("*")):
            if not path.is_file():
                continue
            item = {**fingerprint(path), "bytes": path.stat().st_size}
            if path.suffix.lower() != ".csv":
                item["text"] = path.read_text(encoding="utf-8-sig")
                report["files"].append(item)
                continue
            dates, instruments, satellites, versions = Counter(), Counter(), Counter(), Counter()
            latitudes, longitudes = [], []
            unique_rows = set()
            with path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                item["columns"] = reader.fieldnames
                count = 0
                for row in reader:
                    count += 1
                    dates[date.fromisoformat(row["acq_date"]).isoformat()] += 1
                    instruments[row["instrument"]] += 1
                    satellites[row["satellite"]] += 1
                    versions[row["version"]] += 1
                    latitudes.append(float(row["latitude"]))
                    longitudes.append(float(row["longitude"]))
                    unique_rows.add(tuple(row.values()))
            points = shapely.points(longitudes, latitudes)
            mask = shapely.covers(kaduna, points)
            item.update(rows=count, first_date=min(dates) if dates else None,
                        last_date=max(dates) if dates else None,
                        distinct_observation_dates=len(dates), dates=dict(sorted(dates.items())),
                        instrument=dict(instruments), satellite=dict(satellites), version=dict(versions),
                        exact_duplicate_rows=count - len(unique_rows),
                        coordinate_extent={"latitude": [min(latitudes), max(latitudes)],
                                           "longitude": [min(longitudes), max(longitudes)]} if count else None,
                        kaduna_rows=int(mask.sum()),
                        within_nigeria_adm1_union=int(shapely.covers(nigeria, points).sum()))
            report["files"].append(item)
            print(json.dumps({k: v for k, v in item.items() if k != "dates"}), flush=True)
    output = root / "data/processed/download_audit.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
