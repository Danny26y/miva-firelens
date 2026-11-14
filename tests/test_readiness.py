"""Synthetic diagnostic tests; no fire/exposure observations are fabricated."""
from firelens.readiness import holdout_plan, overlap_grid, week_grid, summarize_grid


def test_partial_bounds_and_unknown_exposure():
    grid = week_grid("2024-01-03", "2024-01-08", {"2024-01-03": 2}, {"2024-01-04": 1})
    assert [r["days_inside_observed_bounds"] for r in grid] == [5, 1]
    assert [r["positive_record_count"] for r in grid] == [2, None]
    assert all(r["observed_pixel_exposure"] is None for r in grid)
    summary = summarize_grid(grid)
    assert summary["partial_endpoint_weeks"] == 2
    assert summary["weeks_without_kaduna_records_unknown"] == 1


def test_neither_sensor_has_rows_is_counted_as_unknown():
    grid = overlap_grid("2024-01-01", "2024-01-14", [])
    assert len(grid) == 2
    assert all(g["pair_status"] == "neither_has_records_unknown" for g in grid)


def test_whole_iso_year_holdouts_do_not_leak_test_year():
    pairs = [{"year": y, "season": "DJF"} for y in (2012, 2013, 2023, 2024, 2025, 2026)]
    folds = holdout_plan(pairs, "2012-01-20", "2026-07-31", post_transition_only=True)
    assert [f["held_out_iso_year"] for f in folds] == [2023, 2024, 2025]
    assert all(f["held_out_iso_year"] not in f["training_years"] for f in folds)
    assert all(f["training_positive_pairs"] == 2 and f["test_positive_pairs"] == 1 for f in folds)
    assert all(not f["trained"] for f in folds)
