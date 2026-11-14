"""Exploratory paired-week comparison only, never a scientific correction.

Inner-join area/ISO year/week, using raw detections only. Missing weeks are
unknown, not zero. The caller must verify matching coverage and processing
quality. A paired week is not a matched fire event or satellite overpass.
"""
from .pipeline import DataError


def paired_week_summary(rows):
    indexed = {}
    for row in rows:
        if row["metric"] != "raw_detections":
            continue
        key = (row["area"], row["year"], row["week"])
        sensors = indexed.setdefault(key, {})
        if row["sensor"] in sensors:
            raise DataError(f"duplicate weekly row: {key}, {row['sensor']}")
        sensors[row["sensor"]] = row["count"]
    pairs = [(key, values) for key, values in sorted(indexed.items())
             if "MODIS" in values and "VIIRS_SNPP" in values]
    modis = sum(v["MODIS"] for _, v in pairs)
    viirs = sum(v["VIIRS_SNPP"] for _, v in pairs)
    return {
        "status": "EXPLORATORY_ONLY" if pairs else "INSUFFICIENT_PAIRED_DATA",
        "method": "ratio of summed raw detections in jointly observed ISO weeks",
        "paired_weeks": len(pairs),
        "overlap_iso_years": sorted({key[1] for key, _ in pairs}),
        "modis_total": modis, "viirs_snpp_total": viirs,
        "viirs_to_modis_ratio": viirs / modis if modis else None,
        "warning": "Not a validated correction. Requires equal temporal/spatial coverage; resolution, overpass, cloud, confidence and algorithm differences confound this ratio. No counts are adjusted.",
    }
