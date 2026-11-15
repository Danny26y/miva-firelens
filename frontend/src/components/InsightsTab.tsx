import {
  buildOutlook,
  computeSensorInsights,
  type InsightCard,
  type MonthStats,
  type SensorInsights,
} from "../lib/insights";
import type { Provenance, WeeklyRecord } from "../lib/types";

type Props = {
  weeks: WeeklyRecord[];
  provenance: Provenance;
};

function Card({ card }: { card: InsightCard }) {
  return (
    <article className={`insight-card tone-${card.tone}`}>
      <div className="insight-metric">
        <span className="insight-metric-value">{card.metricValue}</span>
        <span className="insight-metric-label">{card.metricLabel}</span>
      </div>
      <div>
        <h3>{card.headline}</h3>
        <p>{card.detail}</p>
      </div>
    </article>
  );
}

function MonthTable({
  title,
  months,
}: {
  title: string;
  months: MonthStats[];
}) {
  return (
    <section className="insight-table-wrap">
      <h3>{title}</h3>
      <table className="insight-table">
        <thead>
          <tr>
            <th>Month</th>
            <th>Week detection rate</th>
            <th>Share of detections</th>
            <th>Median when present</th>
          </tr>
        </thead>
        <tbody>
          {months.map((m) => (
            <tr key={m.month}>
              <td>{m.name}</td>
              <td>
                <div className="rate-cell">
                  <span
                    className="rate-bar"
                    style={{ width: `${m.detectionWeekRate * 100}%` }}
                  />
                  <span>{Math.round(m.detectionWeekRate * 100)}%</span>
                </div>
              </td>
              <td>{Math.round(m.detectionShare * 100)}%</td>
              <td>
                {m.medianWhenPresent != null
                  ? Math.round(m.medianWhenPresent).toLocaleString()
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function SensorBlock({ insights }: { insights: SensorInsights }) {
  const label =
    insights.sensor === "MODIS" ? "MODIS (Terra + Aqua)" : "VIIRS Suomi-NPP";
  return (
    <div className="insight-sensor">
      <h2>{label}</h2>
      <div className="insight-cards">
        {insights.recommendations.map((card) => (
          <Card key={card.id} card={card} />
        ))}
      </div>
      <MonthTable title={`${label} by month`} months={insights.months} />
    </div>
  );
}

export function InsightsTab({ weeks, provenance }: Props) {
  const modis = computeSensorInsights(weeks, provenance, "MODIS");
  const viirs = computeSensorInsights(weeks, provenance, "VIIRS_SNPP");
  const outlook = buildOutlook(modis, viirs);

  return (
    <div className="insights">
      <section className="insight-intro">
        <h2>Seasonal insights</h2>
        <p>
          Recommendations are historical rates from the Kaduna FIRMS archive:
          the share of ISO weeks in each month that contain ≥1 raw thermal
          detection. They are not calibrated wildfire probabilities and do not
          account for cloud cover or overpass gaps.
        </p>
      </section>

      <section className="insight-cards outlook">
        {outlook.map((card) => (
          <Card key={card.id} card={card} />
        ))}
      </section>

      <SensorBlock insights={modis} />
      <SensorBlock insights={viirs} />

      <div className="callout">
        Day-of-week claims (Sunday, weekend, etc.) cannot be produced from this
        weekly handoff. Month and season rates above use the Monday of each ISO
        week to assign a calendar month.
      </div>
    </div>
  );
}
