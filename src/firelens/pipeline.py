"""Strict input validation and raw weekly detection counts."""
import csv
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from itertools import islice

SENSORS = ("MODIS", "VIIRS_SNPP")
FIELDS = ("area", "year", "week", "sensor", "count", "metric")
COMMON = {"latitude", "longitude", "scan", "track", "acq_date", "acq_time",
          "satellite", "instrument", "confidence", "version", "frp", "daynight"}
PRODUCT_FIELDS = {"MODIS": {"brightness", "bright_t31"},
                  "VIIRS_SNPP": {"bright_ti4", "bright_ti5"}}


class DataError(ValueError):
    """An actionable input or configuration error."""


@dataclass(frozen=True)
class Observation:
    day: date
    latitude: float
    longitude: float
    sensor: str


def parse_date(value):
    """Accept unambiguous ISO dates, slash ISO dates, and ISO timestamps only."""
    value = value.strip()
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    try:
        if len(value) == 10 and value[4] == value[7] == "/":
            return datetime.strptime(value, "%Y/%m/%d").date()
        if len(value) > 10 and value[10] in "T ":
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() != 0:
                raise ValueError("FIRMS acquisition dates must be UTC")
            return parsed.date()
    except ValueError:
        pass
    raise DataError(f"invalid acq_date {value!r}; use YYYY-MM-DD (UTC), YYYY/MM/DD or ISO UTC timestamp")


def load_csv(path, sensor, *, allow_legacy_modis=False):
    return list(iter_csv(path, sensor, allow_legacy_modis=allow_legacy_modis))


def iter_csv(path, sensor, *, allow_legacy_modis=False):
    """Validate incrementally; legacy MODIS 6.03 requires explicit opt-in.

    Consumers must exhaust this iterator to validate the complete file.
    Opt-in does not relabel legacy records as Collection 6.1.
    """
    if sensor not in SENSORS:
        raise DataError(f"unknown sensor {sensor!r}")
    path = Path(path)
    if not path.is_file():
        raise DataError(f"DATA_REQUIRED: missing {path}")
    observation_count = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        names = reader.fieldnames or []
        if len(names) != len(set(names)):
            raise DataError(f"{path}: duplicate column names")
        product_fields = PRODUCT_FIELDS[sensor]
        # NASA historical download exports also use MODIS-style brightness
        # header names for VIIRS. Product identity still comes from row fields.
        if sensor == "VIIRS_SNPP" and not product_fields <= set(names):
            if {"brightness", "bright_t31"} <= set(names):
                product_fields = {"brightness", "bright_t31"}
        missing = (COMMON | product_fields) - set(names)
        if missing:
            raise DataError(f"{path}: missing columns: {', '.join(sorted(missing))}")
        required = COMMON | product_fields
        numeric_fields = {"scan", "track", "frp"} | product_fields
        allowed_modis = {"6.1", "6.1NRT", "61", "61NRT", "61.03"}
        if allow_legacy_modis:
            allowed_modis.add("6.03")
        for line, row in enumerate(reader, 2):
            try:
                if None in row or any(row[k] is None or not row[k].strip()
                                       for k in required):
                    raise DataError("missing values or malformed CSV row")
                lat, lon = float(row["latitude"]), float(row["longitude"])
                if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    raise DataError("coordinates must be finite WGS84 latitude/longitude")
                for key in numeric_fields:
                    number = float(row[key])
                    if not math.isfinite(number) or number < 0:
                        raise DataError(f"invalid {key}")
                time = row["acq_time"].strip()
                if not time.isdigit() or len(time) > 4:
                    raise DataError("acq_time must be UTC HHMM")
                hhmm = int(time)
                if hhmm // 100 > 23 or hhmm % 100 > 59:
                    raise DataError("acq_time must be valid UTC HHMM")
                if row["instrument"].strip().upper() not in ({"MODIS"} if sensor == "MODIS" else {"VIIRS", "SNPP"}):
                    raise DataError("instrument does not match selected sensor")
                satellite = row["satellite"].strip().upper()
                if satellite not in ({"TERRA", "AQUA", "T", "A"} if sensor == "MODIS" else {"N", "SNPP", "SUOMI-NPP", "S-NPP"}):
                    raise DataError("satellite does not match selected product")
                version = row["version"].strip()
                if sensor == "MODIS" and version not in allowed_modis:
                    raise DataError("expected MODIS Collection 6.1 version")
                confidence = row["confidence"].strip().lower()
                if sensor == "VIIRS_SNPP":
                    if confidence not in {"l", "n", "h", "low", "nominal", "high"}:
                        raise DataError("VIIRS confidence must be l/n/h or low/nominal/high")
                elif not 0 <= float(confidence) <= 100:
                    raise DataError("MODIS confidence must be 0..100")
                if row["daynight"].strip().upper() not in {"D", "N"}:
                    raise DataError("daynight must be D or N")
                observation_count += 1
                yield Observation(parse_date(row["acq_date"]), lat, lon, sensor)
            except (ValueError, TypeError) as exc:
                raise DataError(f"{path}: row {line}: {exc}") from exc
    if not observation_count:
        raise DataError(f"DATA_REQUIRED: {path} has no observations; empty input does not establish zero fires")


def kaduna_boundary(path):
    """Read an actual ADM1 FeatureCollection; include polygon edges and holes."""
    from shapely.geometry import shape
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        crs = document.get("crs")
        if crs is not None and crs.get("properties", {}).get("name") not in {
            "urn:ogc:def:crs:OGC:1.3:CRS84", "urn:ogc:def:crs:EPSG::4326", "EPSG:4326"}:
            raise DataError("boundary must use WGS84 longitude/latitude (CRS84 or EPSG:4326)")
        features = document["features"]
        matches = [f for f in features if any(
            str(f.get("properties", {}).get(k, "")).strip().lower() in {"kaduna", "kaduna state"}
            for k in ("shapeName", "NAME_1", "name", "ADM1_EN"))]
        if len(matches) != 1:
            raise DataError("boundary must contain exactly one named Kaduna state feature")
        geometry = shape(matches[0]["geometry"])
        if geometry.geom_type not in {"Polygon", "MultiPolygon"} or geometry.is_empty or not geometry.is_valid:
            raise DataError("Kaduna boundary must be a valid nonempty Polygon/MultiPolygon")
        x1, y1, x2, y2 = geometry.bounds
        if not (-180 <= x1 <= x2 <= 180 and -90 <= y1 <= y2 <= 90):
            raise DataError("boundary coordinates must be WGS84 longitude/latitude")
        return geometry
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DataError(f"{path}: invalid or missing Kaduna GeoJSON: {exc}") from exc


def aggregate(observations, boundary=None):
    from shapely import prepare, points, covers
    if boundary is not None:
        # Prepare the unchanged polygon once for repeated point predicates.
        prepare(boundary)
    counts = Counter()
    iterator = iter(observations)
    while batch := list(islice(iterator, 25000)):
        selected = [True] * len(batch) if boundary is None else covers(
            boundary, points([o.longitude for o in batch], [o.latitude for o in batch]))
        for obs, included in zip(batch, selected):
            if included:
                year, week, _ = obs.day.isocalendar()
                counts[(year, week, obs.sensor)] += 1
    area = "Kaduna State" if boundary is not None else "input_extent"
    return [dict(zip(FIELDS, (area, year, week, sensor, count, "raw_detections")))
            for (year, week, sensor), count in sorted(counts.items())]


def export(rows, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "weekly_fire_counts.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (directory / "weekly_fire_counts.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest()}
