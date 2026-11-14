"""Build small frontend assets from verified outputs, without altering sources."""
import json
from pathlib import Path

from firelens.pipeline import fingerprint

ROOT = Path(__file__).resolve().parents[1]


def build():
    source = ROOT / "data/processed"
    rows = json.loads((source / "historical_calendar.json").read_text())
    manifest = json.loads((source / "manifest.json").read_text())
    comparison = json.loads((source / "historical_comparison.json").read_text())
    assert manifest["status"] == "VERIFIED"
    assert len(rows) == manifest["weekly_output_rows"]
    assert sum(r["count"] for r in rows) == manifest["kaduna_observations"] == 571781
    keys = [(r["area"], r["year"], r["week"], r["sensor"], r["metric"]) for r in rows]
    assert len(keys) == len(set(keys))
    assert all(type(r["count"]) is int and r["count"] > 0 for r in rows)
    calendar = [{**r, "record_status": "detections_present", "observation_coverage": "unknown"} for r in rows]
    coverage = {s: {"observed_detection_date_bounds": c["observed_bounds"],
                    "missing_record_weeks": c["absent_kaduna_weeks_unknown_not_zero"],
                    "weekly_rows": c["weekly_rows"], "raw_detections": c["kaduna_rows"]}
                for s, c in manifest["coverage"].items()}
    stats = {k: v for k, v in comparison.items() if k != "pairs"}
    stats["warning"] = comparison["warning"]
    provenance = {"area": "Kaduna State", "quality": "standard archives only; NRT excluded",
                  "metric": "raw_detections", "corrected": False,
                  "total_raw_detections": 571781, "weekly_rows": len(rows), "sensors": coverage,
                  "missing_count_policy": "null/unknown, never zero-filled",
                  "coverage_policy": "positive detection records do not establish complete observation coverage",
                  "modis_version_warning": manifest["modis_version_warning"],
                  "source_hashes": [{"file": n, "sha256": fingerprint(source / n)["sha256"]}
                                    for n in ("historical_calendar.json", "historical_comparison.json", "manifest.json")],
                  "boundary": {"source": "geoBoundaries / GRID3, Nigeria ADM1, reference year 2022",
                               "license": "CC BY 4.0", "url": "https://www.geoboundaries.org/",
                               "sha256": manifest["boundary"]["sha256"]},
                  "limitations": ["MODIS 6.03/61.03 processing lineage unresolved", "observation exposure unavailable",
                                  "raw thermal detections include non-vegetation sources and repeat detections",
                                  "positive-pair comparison is descriptive and selected; harmonization unvalidated"]}
    return {"weekly_fire_counts.json": calendar, "comparison.json": stats,
            "paired_weeks.json": comparison["pairs"], "provenance.json": provenance}


def main():
    target = ROOT / "frontend/public/data"
    target.mkdir(parents=True, exist_ok=True)
    for name, value in build().items():
        path = target / name
        path.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
        print(f"{path.relative_to(ROOT)}: {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
