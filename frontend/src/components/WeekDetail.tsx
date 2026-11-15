import type { CalendarCell, Provenance } from "../lib/types";

type Props = {
  cell: CalendarCell | null;
  provenance: Provenance;
};

export function WeekDetail({ cell, provenance }: Props) {
  if (!cell) {
    return (
      <aside className="detail" aria-live="polite">
        <h3>Week inspector</h3>
        <p className="note">
          Select an ISO week cell to inspect raw detection counts, date bounds,
          and coverage status. Empty gray cells are gaps — not confirmed zero
          fires.
        </p>
      </aside>
    );
  }

  const sensorLabel =
    cell.sensor === "MODIS" ? "MODIS (Terra + Aqua)" : "VIIRS Suomi-NPP";

  const statusCopy =
    cell.status === "detections_present"
      ? "Detection records present for this ISO week"
      : cell.status === "missing_within_span"
        ? "No detection records in the supplied archive for this week (exposure unknown)"
        : "Outside the documented observation span for this sensor";

  return (
    <aside className="detail" aria-live="polite">
      <h3>
        {cell.year} · ISO week {cell.week}
      </h3>
      <dl>
        <dt>Sensor</dt>
        <dd>{sensorLabel}</dd>
        <dt>UTC week</dt>
        <dd>
          {cell.monday ?? "—"} → {cell.sunday ?? "—"}
        </dd>
        <dt>Raw detections</dt>
        <dd>{cell.count === null ? "null (gap)" : cell.count.toLocaleString()}</dd>
        <dt>Metric</dt>
        <dd>{provenance.metric}</dd>
        <dt>Status</dt>
        <dd>{statusCopy}</dd>
      </dl>
      {cell.sensor === "MODIS" && cell.year >= 2023 && (
        <p className="note">{provenance.modis_version_warning}</p>
      )}
      {cell.count !== null && (
        <p className="note">
          Counts are repeated thermal detections, not unique fire events or
          burned area.
        </p>
      )}
    </aside>
  );
}
