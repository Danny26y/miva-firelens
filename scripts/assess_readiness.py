"""Write new readiness diagnostics; preserve every original/verified artifact."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from firelens.pipeline import fingerprint
from firelens.readiness import holdout_plan, overlap_grid, ratio_summary, summarize_grid, week_grid

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/readiness/2026-11-14")
    args = parser.parse_args()
    destination = args.output_dir
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Use a new output directory to preserve this assessment: {destination}")
    protected = [p for folder in ("data/raw", "data/processed") for p in (ROOT / folder).rglob("*") if p.is_file()]
    inventory = read(ROOT / "data/processed/historical_inventory.json")
    protected += [Path(f["path"]) for f in inventory["files"]]
    protected += [ROOT / "data/boundaries/nigeria_adm1.geojson"]
    before = [fingerprint(path) for path in protected]
    for f in inventory["files"]:
        assert fingerprint(f["path"])["sha256"] == f["sha256"]
    quality = read(ROOT / "data/processed/historical_quality.json")
    rows = read(ROOT / "data/processed/weekly_fire_counts.json")
    comparison = read(ROOT / "data/processed/historical_comparison.json")
    by_path = {f["path"]: f for f in inventory["files"]}
    grids, year_seasons, year_totals, summaries = [], [], [], []
    for q in quality:
        item = by_path[q["source"]]
        grid = week_grid(item["first_date"], item["last_date"], q["kaduna_dates"], item["dates"])
        label = {"sensor": q["sensor"], "quality": q["quality"]}
        for g in grid:
            grids.append({**label, **g})
        summaries.append({**label, **summarize_grid(grid)})
        for y in sorted({g["year"] for g in grid}):
            selected = [g for g in grid if g["year"] == y]
            year_totals.append({**label, "iso_year": y, **summarize_grid(selected)})
            for season in ("DJF", "MAM", "JJA", "SON"):
                year_seasons.append({**label, "iso_year": y, "season": season,
                                     **summarize_grid([g for g in selected if g["season"] == season])})
    start, end = comparison["overlap_date_bounds"]
    common = overlap_grid(start, end, rows)
    full_common = [g for g in common if not g["partial_at_observed_bounds"]]
    categories = dict(Counter(g["pair_status"] for g in full_common))
    assert categories.get("both_positive", 0) == len(comparison["pairs"])
    pairs = comparison["pairs"]
    ratios = {
        "overall": ratio_summary(pairs),
        "by_month": {str(m): ratio_summary([p for p in pairs if p["month"] == m]) for m in range(1, 13)},
        "by_season": {s: ratio_summary([p for p in pairs if p["season"] == s]) for s in ("DJF", "MAM", "JJA", "SON")},
        "by_iso_year": {str(y): ratio_summary([p for p in pairs if p["year"] == y]) for y in sorted({p["year"] for p in pairs})}}
    result = {"decision": "RAW_VISUALIZATION_READY_CALIBRATION_BLOCKED", "models_trained": False,
              "coverage_definition": "Counts of positive detection dates/records only; no actual observation-exposure denominator is available.",
              "source_quality_summaries": summaries,
              "overlap": {"observed_bounds": [start, end], "calendar_weeks": len(common),
                          "partial_endpoint_weeks": len(common) - len(full_common),
                          "full_calendar_weeks": len(full_common), "full_week_record_categories": categories},
              "overlap_by_iso_year_season": [{"iso_year": y, "season": s,
                  "full_calendar_weeks": len(sample := [g for g in full_common if g["year"] == y and g["season"] == s]),
                  "record_categories": dict(Counter(g["pair_status"] for g in sample))}
                  for y in sorted({g["year"] for g in full_common}) for s in ("DJF", "MAM", "JJA", "SON")],
              "ratios": ratios, "whole_year_holdouts_all_eras": holdout_plan(pairs, start, end),
              "whole_year_holdouts_post_transition": holdout_plan(pairs, start, end, post_transition_only=True)}
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "readiness_diagnostics.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    for name, records in (("weekly_record_availability.csv", grids), ("year_season_record_availability.csv", year_seasons),
                          ("year_record_availability.csv", year_totals)):
        with (destination / name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    for dimension in ("month", "season", "iso_year"):
        records = [{dimension: key, **values} for key, values in ratios[f"by_{dimension}"].items()]
        fields = list(dict.fromkeys(key for row in records for key in row))
        with (destination / f"ratios_by_{dimension}.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
    after = [fingerprint(path) for path in protected]
    assert before == after, "Protected data or exports changed"
    (destination / "preservation_hashes.json").write_text(json.dumps({"status": "UNCHANGED", "files": after}, indent=2) + "\n")
    print(json.dumps({"output": str(destination), "protected_files_unchanged": len(after),
                      "summaries": summaries, "overlap": result["overlap"],
                      "year_ratios": ratios["by_iso_year"], "recent_holdouts": result["whole_year_holdouts_post_transition"]}, indent=2))


if __name__ == "__main__":
    main()
