import { useMemo, useState } from "react";
import type { Aggregates } from "../lib/data";
import { collectionBBox, projectPath, type StateCollection } from "../lib/geo";
import { MONTH_NAMES } from "../lib/insights";
import type { AppPage } from "./AppShell";
import type { Provenance, Sensor } from "../lib/types";

type Props = {
  states: StateCollection;
  provenance: Provenance;
  aggregates: Aggregates;
  onNavigate: (page: AppPage) => void;
};

const WIDTH = 720;
const HEIGHT = 520;

export function MapPage({ states, provenance, aggregates, onNavigate }: Props) {
  const [sensor, setSensor] = useState<Sensor | "BOTH">("BOTH");
  const bbox = useMemo(() => collectionBBox(states.features), [states]);
  const kaduna = states.features.find((f) => f.properties.focus);
  const coverage =
    sensor === "BOTH"
      ? null
      : provenance.sensors[sensor];

  const monthMax = Math.max(
    ...aggregates.by_month.map((m) =>
      sensor === "MODIS"
        ? m.MODIS
        : sensor === "VIIRS_SNPP"
          ? m.VIIRS_SNPP
          : m.MODIS + m.VIIRS_SNPP,
    ),
    1,
  );

  const totalForSensor =
    sensor === "MODIS"
      ? provenance.sensors.MODIS.raw_detections
      : sensor === "VIIRS_SNPP"
        ? provenance.sensors.VIIRS_SNPP.raw_detections
        : provenance.total_raw_detections;

  return (
    <div className="workspace map-page">
      <div className="page-head">
        <div>
          <h1>Historical fire map</h1>
          <p className="lede">
            Kaduna State boundary on the Nigeria ADM1 layer. Point hotspots are
            not in the weekly handoff — intensity below uses monthly raw
            detection totals.
          </p>
        </div>
      </div>

      <div className="disclosure">
        Boundary: {provenance.boundary.source} ({provenance.boundary.license}).
        Activity values are weekly aggregates rolled to calendar month — not
        pixel footprints.
      </div>

      <div className="controls">
        <button
          type="button"
          className={`control-chip${sensor === "BOTH" ? " active" : ""}`}
          aria-pressed={sensor === "BOTH"}
          onClick={() => setSensor("BOTH")}
        >
          Both sensors
        </button>
        <button
          type="button"
          className={`control-chip${sensor === "MODIS" ? " active" : ""}`}
          aria-pressed={sensor === "MODIS"}
          onClick={() => setSensor("MODIS")}
        >
          MODIS
        </button>
        <button
          type="button"
          className={`control-chip${sensor === "VIIRS_SNPP" ? " active" : ""}`}
          aria-pressed={sensor === "VIIRS_SNPP"}
          onClick={() => setSensor("VIIRS_SNPP")}
        >
          VIIRS
        </button>
      </div>

      <div className="map-layout">
        <section className="map-stage panel-card">
          <svg
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            role="img"
            aria-label="Nigeria states with Kaduna highlighted"
            className="nigeria-map"
          >
            {states.features.map((f) => {
              const focus = Boolean(f.properties.focus);
              return (
                <path
                  key={f.properties.name}
                  d={projectPath(f, bbox, WIDTH, HEIGHT)}
                  className={focus ? "state focus" : "state"}
                >
                  <title>{f.properties.name}</title>
                </path>
              );
            })}
          </svg>
          <div className="map-legend">
            <span><i className="swatch focus" /> Kaduna (focus)</span>
            <span><i className="swatch other" /> Other states</span>
          </div>
        </section>

        <aside className="state-panel panel-card">
          <p className="eyebrow">State panel</p>
          <h2>Kaduna</h2>
          <div className="kpi-mini">
            <div>
              <strong>{totalForSensor.toLocaleString()}</strong>
              <span>raw detections</span>
            </div>
            <div>
              <strong>{provenance.weekly_rows.toLocaleString()}</strong>
              <span>positive weeks</span>
            </div>
          </div>
          {coverage ? (
            <p className="muted">
              {coverage.observed_detection_date_bounds[0]} →{" "}
              {coverage.observed_detection_date_bounds[1]}
            </p>
          ) : (
            <p className="muted">
              MODIS {provenance.sensors.MODIS.observed_detection_date_bounds[0]} →{" "}
              {provenance.sensors.MODIS.observed_detection_date_bounds[1]}
              <br />
              VIIRS {provenance.sensors.VIIRS_SNPP.observed_detection_date_bounds[0]} →{" "}
              {provenance.sensors.VIIRS_SNPP.observed_detection_date_bounds[1]}
            </p>
          )}
          <p className="muted">
            {kaduna
              ? `${kaduna.properties.name} · ${kaduna.properties.iso ?? "NG-KD"}`
              : "Kaduna boundary loaded from geoBoundaries / GRID3"}
          </p>
          <button type="button" className="btn-primary" onClick={() => onNavigate("calendar")}>
            Choose a week in calendar →
          </button>
          <button type="button" className="btn-ghost" onClick={() => onNavigate("season")}>
            Read this season’s briefing →
          </button>
        </aside>
      </div>

      <section className="panel-card">
        <div className="panel-card-head">
          <div>
            <h2>Historical monthly activity</h2>
            <p>
              Sum of positive weekly counts whose ISO-week Monday falls in each
              calendar month.
            </p>
          </div>
        </div>
        <div className="month-bars">
          {aggregates.by_month.map((m) => {
            const value =
              sensor === "MODIS"
                ? m.MODIS
                : sensor === "VIIRS_SNPP"
                  ? m.VIIRS_SNPP
                  : m.MODIS + m.VIIRS_SNPP;
            const pct = (value / monthMax) * 100;
            return (
              <div className="month-bar" key={m.month}>
                <span className="month-label">{MONTH_NAMES[m.month - 1].slice(0, 3)}</span>
                <div className="month-track">
                  <div className="month-fill" style={{ height: `${pct}%` }} />
                </div>
                <span className="month-value">{value.toLocaleString()}</span>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
