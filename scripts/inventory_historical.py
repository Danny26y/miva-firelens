"""Streaming inventory of every file in the supplied DL_FIRE directories."""
import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from firelens.pipeline import fingerprint


def main():
    root = Path(__file__).resolve().parents[1]
    report = {"files": [], "scope_warning": "Observed coordinates/dates do not establish complete requested geographic or satellite coverage."}
    for folder in sorted(root.glob("DL_FIRE*")):
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            item = {**fingerprint(path), "bytes": path.stat().st_size}
            if path.suffix.lower() != ".csv":
                item["text"] = path.read_text(encoding="utf-8-sig")
            else:
                dates, versions, satellites, instruments, types = [Counter() for _ in range(5)]
                vd = defaultdict(list)
                minimum = [float("inf"), float("inf")]
                maximum = [float("-inf"), float("-inf")]
                count = 0
                with path.open(encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle)
                    item["columns"] = reader.fieldnames
                    for row in reader:
                        d = date.fromisoformat(row["acq_date"]).isoformat()
                        count += 1
                        dates[d] += 1
                        v = row["version"]
                        versions[v] += 1
                        if not vd[v]:
                            vd[v] = [d, d]
                        vd[v] = [min(vd[v][0], d), max(vd[v][1], d)]
                        satellites[row["satellite"]] += 1
                        instruments[row["instrument"]] += 1
                        types[row.get("type", "not_supplied")] += 1
                        for axis, field in enumerate(("latitude", "longitude")):
                            coordinate = float(row[field])
                            minimum[axis] = min(minimum[axis], coordinate)
                            maximum[axis] = max(maximum[axis], coordinate)
                item.update(rows=count, first_date=min(dates), last_date=max(dates),
                            observation_dates=len(dates), dates=dict(sorted(dates.items())),
                            versions=dict(versions), version_date_ranges=dict(vd),
                            satellites=dict(satellites), instruments=dict(instruments), types=dict(types),
                            extent={"latitude": [minimum[0], maximum[0]], "longitude": [minimum[1], maximum[1]]})
            report["files"].append(item)
            print(json.dumps({k: v for k, v in item.items() if k != "dates"}), flush=True)
    destination = root / "data/processed/historical_inventory.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
