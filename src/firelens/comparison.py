"""Descriptive raw paired-week statistics. No correction is fitted or applied."""
from datetime import date, timedelta
from math import log1p
from statistics import correlation


def quantile(values, probability):
    """Linear interpolation at (n-1)*p; null for an empty sample."""
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def describe(pairs):
    ratios = [p["VIIRS_SNPP"] / p["MODIS"] for p in pairs if p["MODIS"] > 0]
    m, v = sum(p["MODIS"] for p in pairs), sum(p["VIIRS_SNPP"] for p in pairs)
    q1, q3 = quantile(ratios, .25), quantile(ratios, .75)
    result = {"n": len(pairs), "modis_total": m, "viirs_snpp_total": v,
              "summed_count_ratio": v / m if m > 0 else None,
              "weekly_ratio_median": quantile(ratios, .5), "weekly_ratio_q1": q1,
              "weekly_ratio_q3": q3, "weekly_ratio_iqr": q3 - q1 if ratios else None}
    if len(pairs) > 2 and len({p["MODIS"] for p in pairs}) > 1 and len({p["VIIRS_SNPP"] for p in pairs}) > 1:
        result["raw_pearson_r"] = correlation([p["MODIS"] for p in pairs], [p["VIIRS_SNPP"] for p in pairs])
        result["log1p_pearson_r"] = correlation([log1p(p["MODIS"]) for p in pairs], [log1p(p["VIIRS_SNPP"]) for p in pairs])
    return result


def compare_weeks(rows, start, end):
    """Use positive pairs in full ISO weeks inside common observed date bounds.

    Bounds are not proof of complete daily coverage. Absent sensor-week rows
    are unknown, not zeros. Calendar seasons use ISO Thursday month.
    """
    indexed = {}
    for row in rows:
        if row["metric"] != "raw_detections":
            continue
        key = (row["area"], row["year"], row["week"])
        values = indexed.setdefault(key, {})
        if row["sensor"] in values:
            raise ValueError(f"duplicate output key: {key}, {row['sensor']}")
        values[row["sensor"]] = row["count"]
    pairs = []
    excluded = {"partial_edge_weeks": 0, "missing_sensor_weeks": 0, "nonpositive_pairs": 0}
    for (area, year, week), values in sorted(indexed.items()):
        monday = date.fromisocalendar(year, week, 1)
        if monday < start or monday + timedelta(days=6) > end:
            excluded["partial_edge_weeks"] += 1
            continue
        if not {"MODIS", "VIIRS_SNPP"} <= values.keys():
            excluded["missing_sensor_weeks"] += 1
            continue
        if min(values["MODIS"], values["VIIRS_SNPP"]) <= 0:
            excluded["nonpositive_pairs"] += 1
            continue
        thursday = monday + timedelta(days=3)
        season = "DJF" if thursday.month in (12, 1, 2) else "MAM" if thursday.month in (3, 4, 5) else "JJA" if thursday.month in (6, 7, 8) else "SON"
        era = "version_6.03" if monday + timedelta(days=6) < date(2023, 1, 1) else "version_61.03" if monday >= date(2023, 1, 1) else "transition_week"
        pairs.append({"area": area, "year": year, "week": week, "monday": monday.isoformat(),
                      "month": thursday.month, "season": season, "modis_version_era": era,
                      "MODIS": values["MODIS"], "VIIRS_SNPP": values["VIIRS_SNPP"]})
    return {"status": "DESCRIPTIVE_ONLY", "overlap_date_bounds": [start.isoformat(), end.isoformat()],
            "method": "positive paired full ISO weeks; ratio VIIRS_SNPP/MODIS; no imputation or fitted correction",
            "quantiles": "linear interpolation at (n-1)*p",
            "overall": describe(pairs), "excluded_observed_week_keys": excluded,
            "modis_at_least_10_sensitivity": describe([p for p in pairs if p["MODIS"] >= 10]),
            "by_season": {s: describe([p for p in pairs if p["season"] == s]) for s in ("DJF", "MAM", "JJA", "SON")},
            "by_month": {str(m): describe([p for p in pairs if p["month"] == m]) for m in range(1, 13)},
            "by_modis_version_era": {s: describe([p for p in pairs if p["modis_version_era"] == s]) for s in ("version_6.03", "version_61.03", "transition_week")},
            "pairs": pairs,
            "warning": "Positive-pair selection bias; unmatched weeks unknown, not zero. Bounds do not verify overpasses or cloud coverage. Small denominators, season, platform, collection, resolution and algorithm differences confound ratios. No scientific validation or correction."}
