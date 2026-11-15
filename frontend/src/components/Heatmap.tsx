import { fireColor, legendStops } from "../lib/colors";
import {
  MONTH_TICKS,
  resolveCell,
  weeksInIsoYear,
  yearRangeForSensor,
} from "../lib/calendar";
import type {
  CalendarCell,
  Provenance,
  ScaleMode,
  Sensor,
  WeeklyRecord,
} from "../lib/types";

type Props = {
  sensor: Sensor;
  weeks: WeeklyRecord[];
  provenance: Provenance;
  index: Map<string, WeeklyRecord>;
  missing: Set<string>;
  max: number;
  scale: ScaleMode;
  selected: CalendarCell | null;
  onSelect: (cell: CalendarCell) => void;
};

export function Heatmap({
  sensor,
  weeks,
  provenance,
  index,
  missing,
  max,
  scale,
  selected,
  onSelect,
}: Props) {
  const years = yearRangeForSensor(weeks, sensor);
  const coverage = provenance.sensors[sensor];
  const firstYear = years[0] ?? 0;
  const lastYear = years[years.length - 1] ?? 0;
  const stops = legendStops(max, scale);
  const title = sensor === "MODIS" ? "MODIS (Terra + Aqua)" : "VIIRS Suomi-NPP";

  return (
    <section className="calendar-panel" aria-label={`${title} weekly calendar`}>
      <div className="panel-head">
        <h2>{title}</h2>
        <div className="bounds">
          {coverage.observed_detection_date_bounds[0]} →{" "}
          {coverage.observed_detection_date_bounds[1]} ·{" "}
          {coverage.raw_detections.toLocaleString()} detections
        </div>
      </div>

      <div className="heatmap" role="grid" aria-rowcount={years.length}>
        <div aria-hidden="true" />
        <div className="month-row" aria-hidden="true">
          {MONTH_TICKS.map((tick) => (
            <span
              key={tick.label}
              style={{ gridColumn: tick.week }}
            >
              {tick.label}
            </span>
          ))}
        </div>

        {years.map((year) => {
          const nWeeks = weeksInIsoYear(year);
          const showEra = sensor === "MODIS" && year === 2023;
          return (
            <div className="year-row" key={year} role="row">
              <div
                className={`year-label${showEra ? " era-break" : ""}`}
                title={
                  showEra
                    ? provenance.modis_version_warning
                    : undefined
                }
              >
                {year}
              </div>
              <div className="cells">
                {Array.from({ length: 53 }, (_, i) => {
                  const week = i + 1;
                  if (week > nWeeks) {
                    return (
                      <span
                        key={week}
                        className="cell"
                        data-status="outside_span"
                        aria-hidden="true"
                      />
                    );
                  }
                  const cell = resolveCell(
                    year,
                    week,
                    sensor,
                    index,
                    missing,
                    { first: firstYear, last: lastYear },
                  );
                  const isSelected =
                    selected?.year === year &&
                    selected?.week === week &&
                    selected?.sensor === sensor;
                  const label =
                    cell.count === null
                      ? `${year} W${week}: no detection records`
                      : `${year} W${week}: ${cell.count.toLocaleString()} raw detections`;
                  return (
                    <button
                      key={week}
                      type="button"
                      className="cell"
                      role="gridcell"
                      data-status={cell.status}
                      aria-label={label}
                      aria-pressed={isSelected}
                      title={label}
                      style={{
                        background:
                          cell.count === null
                            ? undefined
                            : fireColor(cell.count, max, scale),
                      }}
                      onClick={() => onSelect(cell)}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div className="legend">
        <span>Fewer</span>
        <div className="legend-ramp" aria-hidden="true">
          {stops.map((s) => (
            <span key={s.label} style={{ background: s.color }} title={s.label} />
          ))}
        </div>
        <span>More (max {max.toLocaleString()})</span>
        <span className="legend-gap">
          <i /> No detection records / unknown exposure
        </span>
      </div>
    </section>
  );
}
