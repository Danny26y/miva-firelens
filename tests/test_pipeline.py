import csv
import json
from datetime import date
from pathlib import Path

import pytest
from shapely.geometry import Polygon, mapping

from firelens.cli import main
from firelens.harmonization import paired_week_summary
from firelens.pipeline import (DataError, Observation, aggregate, export,
                               kaduna_boundary, load_csv, parse_date)

FIXTURES = Path(__file__).parent / "fixtures"


def test_ingestion_both_products():
    assert len(load_csv(FIXTURES / "synthetic_modis.csv", "MODIS")) == 3
    assert len(load_csv(FIXTURES / "synthetic_viirs.csv", "VIIRS_SNPP")) == 2


@pytest.mark.parametrize("text", ["2021-01-01", "2021/01/01", "2021-01-01T00:00:00Z", "2021-01-01 00:00:00+00:00"])
def test_dates(text):
    assert parse_date(text) == date(2021, 1, 1)


@pytest.mark.parametrize("text", ["01/02/2021", "2021-02-29", "", "2021-01-01T12:00:00+01:00"])
def test_bad_dates(text):
    with pytest.raises(DataError):
        parse_date(text)


def test_iso_boundary_and_raw_duplicates():
    observations = load_csv(FIXTURES / "synthetic_modis.csv", "MODIS")
    rows = aggregate(observations)
    assert [(r["year"], r["week"], r["count"]) for r in rows] == [(2020, 53, 2), (2021, 1, 1)]
    assert all(r["metric"] == "raw_detections" and r["area"] == "input_extent" for r in rows)
    assert aggregate(observations + observations)[0]["count"] == 4


def test_sensors_stay_separate():
    obs = load_csv(FIXTURES / "synthetic_modis.csv", "MODIS") + load_csv(FIXTURES / "synthetic_viirs.csv", "VIIRS_SNPP")
    rows = aggregate(obs)
    assert len(rows) == 4
    assert sum(r["count"] for r in rows) == 5


@pytest.mark.parametrize("old,new", [
    ("latitude,", "wrong,"), ("2020-12-31", "not-a-date"),
    ("10,7,330", "nan,7,330"), ("10,7,330", "91,7,330"),
    ("10,7,330", ",7,330"), (",0030,", ",2560,"),
    (",6.1,", ",6.0,"), (",MODIS,", ",VIIRS,"),
    (",Terra,", ",NOAA20,"), (",80,", ",101,"),
])
def test_invalid_rows_have_useful_errors(tmp_path, old, new):
    path = tmp_path / "bad.csv"
    path.write_text((FIXTURES / "synthetic_modis.csv").read_text().replace(old, new), encoding="utf-8")
    with pytest.raises(DataError, match=r"bad.csv.*(row 2|missing columns)"):
        load_csv(path, "MODIS")


def test_missing_and_empty_data(tmp_path):
    with pytest.raises(DataError, match="DATA_REQUIRED"):
        load_csv(tmp_path / "missing.csv", "MODIS")
    path = tmp_path / "empty.csv"
    path.write_text((FIXTURES / "synthetic_modis.csv").read_text().splitlines()[0] + "\n")
    with pytest.raises(DataError, match="no observations"):
        load_csv(path, "MODIS")
    assert main(["--modis", str(path), "--viirs", str(tmp_path / "absent.csv"), "--output-dir", str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out").exists()


def test_polygon_edges_holes_and_area(tmp_path):
    # SYNTHETIC polygon: tests geometry behavior, never actual state geography.
    polygon = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)], holes=[[(1, 1), (2, 1), (2, 2), (1, 2)]])
    path = tmp_path / "synthetic.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"shapeName": "Kaduna"}, "geometry": mapping(polygon)}]}))
    boundary = kaduna_boundary(path)
    points = [(0, 0), (3, 3), (1.5, 1.5), (8, 8)]
    rows = aggregate([Observation(date(2021, 1, 1), lat, lon, "MODIS") for lat, lon in points], boundary)
    assert rows[0]["count"] == 2
    assert rows[0]["area"] == "Kaduna State"
    path.write_text('{"features": []}')
    with pytest.raises(DataError, match="exactly one"):
        kaduna_boundary(path)


def test_export_and_cli(tmp_path):
    args = ["--modis", str(FIXTURES / "synthetic_modis.csv"), "--viirs", str(FIXTURES / "synthetic_viirs.csv"), "--output-dir", str(tmp_path), "--exploratory"]
    assert main(args) == 0
    rows = json.loads((tmp_path / "weekly_fire_counts.json").read_text())
    with (tmp_path / "weekly_fire_counts.csv").open(newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(rows) == len(csv_rows) == 4
    assert [int(r["count"]) for r in csv_rows] == [r["count"] for r in rows]
    assert list(rows[0]) == ["area", "year", "week", "sensor", "count", "metric"]
    assert json.loads((tmp_path / "manifest.json").read_text())["selected_observations"] == 5
    assert json.loads((tmp_path / "exploratory_harmonization.json").read_text())["paired_weeks"] == 2
    assert main(args) == 0  # reproducible ordering and values
    assert rows == json.loads((tmp_path / "weekly_fire_counts.json").read_text())


def test_empty_export_is_not_fabricated_zero(tmp_path):
    export([], tmp_path)
    assert json.loads((tmp_path / "weekly_fire_counts.json").read_text()) == []
    assert len((tmp_path / "weekly_fire_counts.csv").read_text().splitlines()) == 1


def test_harmonization_uses_only_paired_weeks():
    rows = aggregate(load_csv(FIXTURES / "synthetic_modis.csv", "MODIS") + load_csv(FIXTURES / "synthetic_viirs.csv", "VIIRS_SNPP"))
    result = paired_week_summary(rows)
    assert result["viirs_to_modis_ratio"] == pytest.approx(2 / 3)
    assert result["status"] == "EXPLORATORY_ONLY"
    assert paired_week_summary(rows[:1])["status"] == "INSUFFICIENT_PAIRED_DATA"
    with pytest.raises(DataError, match="duplicate"):
        paired_week_summary(rows + rows)


def test_actual_boundary_integration():
    from shapely.geometry import Point
    boundary = kaduna_boundary(Path(__file__).parents[1] / "data/boundaries/nigeria_adm1.geojson")
    # Kaduna city is inside; Abuja is outside. These are geometry checks only,
    # not fire observations and never enter a production export.
    assert boundary.covers(Point(7.44, 10.52))
    assert not boundary.covers(Point(7.49, 9.06))


def test_kaduna_requires_boundary(tmp_path):
    assert main(["--modis", str(FIXTURES / "synthetic_modis.csv"),
                 "--viirs", str(FIXTURES / "synthetic_viirs.csv"),
                 "--area", "kaduna", "--boundary", str(tmp_path / "missing.geojson"),
                 "--output-dir", str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out").exists()


def test_modis_archive_version_regression(tmp_path):
    # SYNTHETIC rows with the version spelling observed in the real archive.
    path = tmp_path / "synthetic_archive_modis.csv"
    path.write_text((FIXTURES / "synthetic_modis.csv").read_text().replace(",6.1,", ",61.03,"))
    assert len(load_csv(path, "MODIS")) == 3


def test_snpp_download_schema_regression(tmp_path):
    # SYNTHETIC rows with the NASA archive download's column/platform aliases.
    text = (FIXTURES / "synthetic_viirs.csv").read_text()
    text = text.replace("bright_ti4", "brightness").replace("bright_ti5", "bright_t31")
    text = text.replace(",N,VIIRS,", ",SNPP,SNPP,")
    path = tmp_path / "synthetic_archive_snpp.csv"
    path.write_text(text)
    assert len(load_csv(path, "VIIRS_SNPP")) == 2
    path.write_text(text.replace(",SNPP,SNPP,", ",NOAA20,SNPP,"))
    with pytest.raises(DataError, match="satellite"):
        load_csv(path, "VIIRS_SNPP")
