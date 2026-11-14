"""Prepare matched standard-quality archive intervals; preserve all originals.

Run audit_downloads.py first. No NRT rows or inferred zero observations enter
the canonical files. Expected filename suffix 'nigeria' is a legacy convention,
not an assertion that every supplied point lies inside Nigeria's boundary.
"""
import csv
import json
from pathlib import Path

from firelens.pipeline import fingerprint


def main():
    root = Path(__file__).resolve().parents[1]
    audit = json.loads((root / "data/processed/download_audit.json").read_text())
    selected = [f for f in audit["files"] if "fire_archive_" in f["path"]]
    assert len(selected) == 2
    by_sensor = {}
    for item in selected:
        if item["instrument"] == {"MODIS": item["rows"]} and item["version"] == {"61.03": item["rows"]}:
            sensor = "MODIS"
        elif item["instrument"] == {"SNPP": item["rows"]} and item["satellite"] == {"SNPP": item["rows"]} and item["version"] == {"2": item["rows"]}:
            sensor = "VIIRS_SNPP"
        else:
            raise ValueError(f"Unrecognized archive product: {item['path']}")
        by_sensor[sensor] = item
    assert set(by_sensor) == {"MODIS", "VIIRS_SNPP"}
    start = max(f["first_date"] for f in selected)
    end = min(f["last_date"] for f in selected)
    assert start <= end
    paired_dates = set(by_sensor["MODIS"]["dates"]) & set(by_sensor["VIIRS_SNPP"]["dates"])
    result = {"selection": "standard archive only; identical inclusive observation-date interval",
              "start": start, "end": end, "joint_detection_dates_before_state_filter": len(paired_dates),
              "geography": "Supplied regional extent; no claim of exact Nigeria-only coverage. CLI must apply actual Kaduna polygon.",
              "inputs": []}
    for sensor, filename in (("MODIS", "modis_c61_nigeria.csv"), ("VIIRS_SNPP", "viirs_snpp_375m_nigeria.csv")):
        item = by_sensor[sensor]
        source = Path(item["path"])
        assert fingerprint(source)["sha256"] == item["sha256"], "Original changed since audit"
        target = root / "data/raw" / filename
        temporary = target.with_suffix(".preparing")
        count = 0
        with source.open(encoding="utf-8-sig", newline="") as src, temporary.open("w", encoding="utf-8", newline="") as dst:
            reader = csv.DictReader(src)
            writer = csv.DictWriter(dst, fieldnames=reader.fieldnames)
            writer.writeheader()
            for row in reader:
                if start <= row["acq_date"] <= end:
                    writer.writerow(row)
                    count += 1
        prepared = fingerprint(temporary)
        if target.exists():
            if fingerprint(target)["sha256"] != prepared["sha256"]:
                raise FileExistsError(f"Refusing to overwrite different existing input: {target}")
            temporary.unlink()
        else:
            temporary.rename(target)
        result["inputs"].append({"sensor": sensor, "source": item["path"],
                                 "source_sha256": item["sha256"],
                                 "prepared": fingerprint(target), "rows": count,
                                 "excluded_outside_common_interval": item["rows"] - count})
    (root / "data/raw/provenance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
