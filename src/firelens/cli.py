import argparse
import json
import sys
from pathlib import Path

from .harmonization import paired_week_summary
from .pipeline import DataError, aggregate, export, fingerprint, kaduna_boundary, load_csv


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline FIRMS raw weekly detection counts")
    parser.add_argument("--modis", type=Path, default=Path("data/raw/modis_c61_nigeria.csv"))
    parser.add_argument("--viirs", type=Path, default=Path("data/raw/viirs_snpp_375m_nigeria.csv"))
    parser.add_argument("--area", choices=("input_extent", "kaduna"), default="input_extent")
    parser.add_argument("--boundary", type=Path, default=Path("data/boundaries/nigeria_adm1.geojson"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--exploratory", action="store_true")
    args = parser.parse_args(argv)
    try:
        missing = [str(p) for p in (args.modis, args.viirs) if not p.is_file()]
        if missing:
            raise DataError("DATA_REQUIRED: missing " + ", ".join(missing) +
                            ". Download NASA FIRMS CSVs using docs/ACQUISITION.md, then rerun. Existing outputs were not refreshed.")
        boundary = kaduna_boundary(args.boundary) if args.area == "kaduna" else None
        observations = load_csv(args.modis, "MODIS") + load_csv(args.viirs, "VIIRS_SNPP")
        rows = aggregate(observations, boundary)
        inputs = [fingerprint(p) for p in (args.modis, args.viirs)]
        if boundary is not None:
            inputs.append(fingerprint(args.boundary))
        export(rows, args.output_dir)
        manifest = {"status": "READY" if rows else "NO_DETECTIONS_IN_SELECTION",
                    "inputs": inputs, "input_observations": len(observations),
                    "selected_observations": sum(r["count"] for r in rows),
                    "rows": len(rows), "missing_weeks": "unknown; not zero-filled",
                    "area": "Kaduna State" if boundary is not None else "input_extent"}
        manifest["observed_dates_by_sensor"] = {
            sensor: {"first": min(o.day for o in observations if o.sensor == sensor).isoformat(),
                     "last": max(o.day for o in observations if o.sensor == sensor).isoformat()}
            for sensor in ("MODIS", "VIIRS_SNPP")}
        (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        if args.exploratory:
            (args.output_dir / "exploratory_harmonization.json").write_text(
                json.dumps(paired_week_summary(rows), indent=2) + "\n", encoding="utf-8")
        print(json.dumps(manifest))
        return 0
    except (DataError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
