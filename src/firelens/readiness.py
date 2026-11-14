"""Read-only descriptive diagnostics; detection-day activity is not exposure."""
from collections import Counter
from datetime import date, timedelta

from .comparison import describe


def season(month):
    return "DJF" if month in (12, 1, 2) else "MAM" if month in (3, 4, 5) else "JJA" if month in (6, 7, 8) else "SON"


def week_grid(first, last, kaduna_dates, regional_dates):
    """Grid observed-date bounds without creating any zero fire-count rows.

    Zero detection_days means zero dates with positive detection records,
    not zero satellite observations. Exposure remains unknown in every row.
    """
    first, last = date.fromisoformat(first), date.fromisoformat(last)
    monday = first - timedelta(days=first.weekday())
    result = []
    while monday <= last:
        days = [monday + timedelta(days=i) for i in range(7)
                if first <= monday + timedelta(days=i) <= last]
        kdays = sum(kaduna_dates.get(d.isoformat(), 0) > 0 for d in days)
        rdays = sum(regional_dates.get(d.isoformat(), 0) > 0 for d in days)
        count = sum(kaduna_dates.get(d.isoformat(), 0) for d in days)
        y, w, _ = monday.isocalendar()
        result.append({"year": y, "week": w, "monday": str(monday),
                       "season": season((monday + timedelta(days=3)).month),
                       "days_inside_observed_bounds": len(days),
                       "partial_at_observed_bounds": len(days) < 7,
                       "kaduna_detection_days": kdays, "regional_detection_days": rdays,
                       "positive_record_count": count if count else None,
                       "observed_pixel_exposure": None,
                       "status": "POSITIVE_DETECTION_RECORDS" if kdays else "NO_DETECTION_RECORDS_EXPOSURE_UNKNOWN"})
        monday += timedelta(days=7)
    return result


def summarize_grid(grid):
    return {"calendar_weeks_in_bounds": len(grid),
            "full_calendar_weeks_in_bounds": sum(not g["partial_at_observed_bounds"] for g in grid),
            "partial_endpoint_weeks": sum(g["partial_at_observed_bounds"] for g in grid),
            "weeks_with_kaduna_records": sum(g["kaduna_detection_days"] > 0 for g in grid),
            "weeks_without_kaduna_records_unknown": sum(g["kaduna_detection_days"] == 0 for g in grid),
            "weeks_without_regional_records_unknown": sum(g["regional_detection_days"] == 0 for g in grid),
            "weeks_with_7_kaduna_detection_days": sum(g["kaduna_detection_days"] == 7 for g in grid),
            "kaduna_detection_days": sum(g["kaduna_detection_days"] for g in grid),
            "regional_detection_days": sum(g["regional_detection_days"] for g in grid),
            "days_inside_bounds": sum(g["days_inside_observed_bounds"] for g in grid),
            "weeks_with_verified_complete_exposure": None}


def overlap_grid(first, last, weekly_rows):
    indexed = {(r["year"], r["week"], r["sensor"]): r["count"] for r in weekly_rows}
    grid = week_grid(first, last, {}, {})
    for g in grid:
        m, v = (indexed.get((g["year"], g["week"], s)) for s in ("MODIS", "VIIRS_SNPP"))
        g["pair_status"] = "both_positive" if m and v else "modis_only" if m else "viirs_only" if v else "neither_has_records_unknown"
    return grid


def ratio_summary(pairs):
    summary = describe(pairs)
    ratios = [p["VIIRS_SNPP"] / p["MODIS"] for p in pairs if p["MODIS"] > 0]
    summary.update(modis_lt10=sum(p["MODIS"] < 10 for p in pairs),
                   modis_eq1=sum(p["MODIS"] == 1 for p in pairs),
                   weekly_ratio_min=min(ratios) if ratios else None,
                   weekly_ratio_max=max(ratios) if ratios else None)
    return summary


def holdout_plan(pairs, first, last, *, post_transition_only=False):
    """Count support for whole-ISO-year holdouts; never train a model."""
    first, last = date.fromisoformat(first), date.fromisoformat(last)
    years = [y for y in range(first.year, last.year + 1)
             if first <= date.fromisocalendar(y, 1, 1)
             and date.fromisocalendar(y + 1, 1, 1) - timedelta(days=1) <= last
             and (not post_transition_only or y >= 2023)]
    eligible = [p for p in pairs if p["year"] in years]
    folds = []
    for year in years:
        train, test = [p for p in eligible if p["year"] != year], [p for p in eligible if p["year"] == year]
        folds.append({"held_out_iso_year": year, "training_years": [y for y in years if y != year],
                      "training_positive_pairs": len(train), "test_positive_pairs": len(test),
                      "training_by_season": {s: sum(p["season"] == s for p in train) for s in ("DJF", "MAM", "JJA", "SON")},
                      "test_by_season": {s: sum(p["season"] == s for p in test) for s in ("DJF", "MAM", "JJA", "SON")},
                      "complete_observation_exposure_verified": False,
                      "trained": False})
    return folds
