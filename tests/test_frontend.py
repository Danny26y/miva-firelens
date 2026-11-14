"""Validate committed real-data handoff against verified sources when available."""
import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_contract_and_totals():
    folder = ROOT / "frontend/public/data"
    rows = json.loads((folder / "weekly_fire_counts.json").read_text())
    provenance = json.loads((folder / "provenance.json").read_text())
    assert len(rows) == 1337
    assert sum(r["count"] for r in rows) == 571781
    keys, totals = set(), Counter()
    for r in rows:
        assert r["area"] == "Kaduna State" and r["metric"] == "raw_detections"
        assert r["record_status"] == "detections_present" and r["observation_coverage"] == "unknown"
        assert type(r["count"]) is int and r["count"] > 0
        date.fromisocalendar(r["year"], r["week"], 1)
        key = (r["year"], r["week"], r["sensor"])
        assert key not in keys
        keys.add(key)
        totals[r["sensor"]] += r["count"]
    assert totals == {"MODIS": 128288, "VIIRS_SNPP": 443493}
    for s, c in provenance["sensors"].items():
        assert all((y, w, s) not in keys for y, w in c["missing_record_weeks"])
    source = ROOT / "data/processed/historical_calendar.json"
    if source.exists():
        original = json.loads(source.read_text())
        assert [{k: r[k] for k in original[0]} for r in rows] == original


def test_frontend_comparison_is_raw_and_consistent():
    folder = ROOT / "frontend/public/data"
    stats = json.loads((folder / "comparison.json").read_text())
    pairs = json.loads((folder / "paired_weeks.json").read_text())
    assert len(pairs) == stats["overall"]["n"] == 410
    assert sum(p["MODIS"] for p in pairs) == stats["overall"]["modis_total"]
    assert sum(p["VIIRS_SNPP"] for p in pairs) == stats["overall"]["viirs_snpp_total"]
    assert stats["status"] == "DESCRIPTIVE_ONLY"
    rows = json.loads((folder / "weekly_fire_counts.json").read_text())
    indexed = {(r["year"], r["week"], r["sensor"]): r["count"] for r in rows}
    for p in pairs:
        assert p["MODIS"] == indexed[p["year"], p["week"], "MODIS"]
        assert p["VIIRS_SNPP"] == indexed[p["year"], p["week"], "VIIRS_SNPP"]
