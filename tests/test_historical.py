"""All observations below are SYNTHETIC unit-test data."""
from datetime import date
from pathlib import Path

import pytest

from firelens.comparison import compare_weeks, quantile
from firelens.pipeline import DataError, Observation, aggregate, iter_csv, load_csv

FIXTURES = Path(__file__).parent / "fixtures"


def test_streaming_matches_existing_counts():
    source = FIXTURES / "synthetic_modis.csv"
    assert aggregate(iter_csv(source, "MODIS")) == aggregate(load_csv(source, "MODIS"))


def test_legacy_modis_is_explicit_opt_in(tmp_path):
    source = tmp_path / "synthetic_legacy.csv"
    source.write_text((FIXTURES / "synthetic_modis.csv").read_text().replace(",6.1,", ",6.03,"))
    with pytest.raises(DataError, match="Collection 6.1"):
        load_csv(source, "MODIS")
    assert len(list(iter_csv(source, "MODIS", allow_legacy_modis=True))) == 3


def row(week, sensor, count):
    return {"area": "SYNTHETIC", "year": 2024, "week": week,
            "sensor": sensor, "count": count, "metric": "raw_detections"}


def test_pairs_missing_zero_and_partial_edges():
    rows = [row(1, "MODIS", 1), row(1, "VIIRS_SNPP", 9),
            row(2, "MODIS", 2), row(2, "VIIRS_SNPP", 8),
            row(3, "MODIS", 0), row(3, "VIIRS_SNPP", 7),
            row(4, "VIIRS_SNPP", 5)]
    result = compare_weeks(rows, date(2024, 1, 2), date(2024, 2, 4))
    assert result["overall"]["n"] == 1
    assert result["overall"]["summed_count_ratio"] == 4
    assert result["excluded_observed_week_keys"] == {"partial_edge_weeks": 1, "missing_sensor_weeks": 1, "nonpositive_pairs": 1}
    assert result["modis_at_least_10_sensitivity"]["summed_count_ratio"] is None


def test_ratio_quantiles_and_duplicate_keys():
    assert quantile([1, 2, 3, 4], .25) == 1.75
    assert quantile([], .5) is None
    rows = [row(1, "MODIS", 1), row(1, "VIIRS_SNPP", 2),
            row(2, "MODIS", 3), row(2, "VIIRS_SNPP", 12)]
    result = compare_weeks(rows, date(2024, 1, 1), date(2024, 1, 14))
    assert result["overall"]["summed_count_ratio"] == 3.5
    assert result["overall"]["weekly_ratio_median"] == 3
    assert result["overall"]["weekly_ratio_iqr"] == 1
    assert result["by_season"]["DJF"]["n"] == 2
    with pytest.raises(ValueError, match="duplicate"):
        compare_weeks(rows + rows[:1], date(2024, 1, 1), date(2024, 1, 14))


def test_bounded_batches_preserve_all_raw_duplicates_and_iso_year():
    observations = (Observation(date(2005, 1, 1), 10, 7, "MODIS") for _ in range(25003))
    result = aggregate(observations)
    assert len(result) == 1
    assert (result[0]["year"], result[0]["week"], result[0]["count"]) == (2004, 53, 25003)


def test_version_transition_week_stays_separate():
    rows = [{"area": "SYNTHETIC", "year": 2022, "week": 52,
             "sensor": s, "count": n, "metric": "raw_detections"}
            for s, n in (("MODIS", 4), ("VIIRS_SNPP", 20))]
    result = compare_weeks(rows, date(2022, 12, 26), date(2023, 1, 1))
    assert result["by_modis_version_era"]["transition_week"]["n"] == 1
    assert result["by_modis_version_era"]["version_61.03"]["n"] == 0
