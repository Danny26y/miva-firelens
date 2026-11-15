import { useEffect, useMemo, useState } from "react";
import { Heatmap } from "./components/Heatmap";
import { SeasonStrip } from "./components/SeasonStrip";
import { WeekDetail } from "./components/WeekDetail";
import {
  buildIndex,
  buildMissingSet,
  maxCount,
} from "./lib/calendar";
import { loadFireLensData, type FireLensData } from "./lib/data";
import type { CalendarCell, ScaleMode, SensorView } from "./lib/types";

export default function App() {
  const [data, setData] = useState<FireLensData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sensorView, setSensorView] = useState<SensorView>("BOTH");
  const [scale, setScale] = useState<ScaleMode>("log");
  const [selected, setSelected] = useState<CalendarCell | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    loadFireLensData(controller.signal)
      .then(setData)
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Failed to load data");
      });
    return () => controller.abort();
  }, []);

  const index = useMemo(
    () => (data ? buildIndex(data.weeks) : new Map()),
    [data],
  );

  const missing = useMemo(() => {
    if (!data) {
      return {
        MODIS: new Set<string>(),
        VIIRS_SNPP: new Set<string>(),
      };
    }
    return {
      MODIS: buildMissingSet(data.provenance.sensors.MODIS.missing_record_weeks),
      VIIRS_SNPP: buildMissingSet(
        data.provenance.sensors.VIIRS_SNPP.missing_record_weeks,
      ),
    };
  }, [data]);

  if (error) {
    return (
      <div className="app">
        <div className="status-banner error">{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="app">
        <div className="status-banner">Loading Kaduna weekly detections…</div>
      </div>
    );
  }

  const { weeks, provenance, comparison } = data;
  const sensors: Array<"MODIS" | "VIIRS_SNPP"> =
    sensorView === "BOTH" ? ["MODIS", "VIIRS_SNPP"] : [sensorView];

  return (
    <div className="app">
      <header className="hero">
        <div className="brand">
          <div className="brand-mark">
            Fire<span>Lens</span>
          </div>
          <div className="brand-meta">
            {provenance.area} · NASA FIRMS raw thermal detections · ISO weeks
          </div>
        </div>
        <h1>Weekly detection calendar</h1>
        <p className="lede">
          {provenance.weekly_rows.toLocaleString()} positive sensor-weeks ·{" "}
          {provenance.total_raw_detections.toLocaleString()} raw detections.
          Gaps stay unknown — never zero-filled. Sensors are not interchangeable.
        </p>
      </header>

      <div className="controls">
        <div>
          <span className="control-label">Sensor</span>
          <div className="segmented" role="group" aria-label="Sensor view">
            {(
              [
                ["BOTH", "Side by side"],
                ["MODIS", "MODIS"],
                ["VIIRS_SNPP", "VIIRS"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={sensorView === value}
                onClick={() => setSensorView(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <span className="control-label">Scale</span>
          <div className="segmented" role="group" aria-label="Color scale">
            {(
              [
                ["log", "Log"],
                ["linear", "Linear"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                aria-pressed={scale === value}
                onClick={() => setScale(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="layout-with-detail">
        <div
          className={`calendar-shell dual${sensorView === "BOTH" ? " side-by-side" : ""}`}
        >
          {sensors.map((sensor) => (
            <Heatmap
              key={sensor}
              sensor={sensor}
              weeks={weeks}
              provenance={provenance}
              index={index}
              missing={missing[sensor]}
              max={maxCount(weeks, sensor)}
              scale={scale}
              selected={selected}
              onSelect={setSelected}
            />
          ))}
        </div>
        <WeekDetail cell={selected} provenance={provenance} />
      </div>

      <SeasonStrip comparison={comparison} />

      <footer className="footer">
        <div>
          Data: NASA FIRMS standard archives (NRT excluded). Boundary:{" "}
          <a href={provenance.boundary.url} rel="noreferrer" target="_blank">
            {provenance.boundary.source}
          </a>{" "}
          ({provenance.boundary.license}).
        </div>
        <div>
          {provenance.limitations.join(" · ")} Metric is{" "}
          <strong style={{ color: "var(--text-muted)", fontWeight: 600 }}>
            {provenance.metric}
          </strong>
          ; corrected={String(provenance.corrected)}.
        </div>
        <div>{provenance.modis_version_warning}</div>
      </footer>
    </div>
  );
}
