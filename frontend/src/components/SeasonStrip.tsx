import type { Comparison } from "../lib/types";

const ORDER = ["DJF", "MAM", "JJA", "SON"] as const;
const LABELS: Record<(typeof ORDER)[number], string> = {
  DJF: "Dec–Feb",
  MAM: "Mar–May",
  JJA: "Jun–Aug",
  SON: "Sep–Nov",
};

type Props = {
  comparison: Comparison;
};

export function SeasonStrip({ comparison }: Props) {
  const seasons = ORDER.map((key) => {
    const row = comparison.by_season[key];
    return {
      key,
      label: LABELS[key],
      n: row?.n ?? 0,
      median: row?.weekly_ratio_median ?? 0,
    };
  });
  const maxN = Math.max(...seasons.map((s) => s.n), 1);

  return (
    <section className="secondary" aria-labelledby="season-heading">
      <h2 id="season-heading">Paired-week seasonality</h2>
      <p className="section-lede">
        Weeks where both sensors have positive counts ({comparison.overall.n}{" "}
        paired). Median VIIRS/MODIS ratio by season — descriptive only, not a
        correction factor.
      </p>
      <div className="season-bars">
        {seasons.map((s, i) => (
          <div className="season-row" key={s.key}>
            <span className="label">{s.key}</span>
            <div className="bar-track" title={s.label}>
              <div
                className="bar-fill"
                style={{
                  width: `${(s.n / maxN) * 100}%`,
                  animationDelay: `${i * 0.06}s`,
                }}
              />
            </div>
            <span className="value">
              n={s.n} · median ratio {s.median.toFixed(1)}
            </span>
          </div>
        ))}
      </div>
      <div className="callout" style={{ marginTop: 16 }}>
        {comparison.warning}
      </div>
    </section>
  );
}
