"""Standalone raw comparison figures; missing weeks are plotted as gaps."""
import json
import os
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".historical-work/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def main():
    out = ROOT / "data/processed"
    charts = out / "charts"
    charts.mkdir(exist_ok=True)
    rows = json.loads((out / "weekly_fire_counts.json").read_text())
    comparison = json.loads((out / "historical_comparison.json").read_text())
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "axes.grid": True, "grid.alpha": .18})
    colors = {"MODIS": "#bd5229", "VIIRS_SNPP": "#166980"}

    def save(fig, name):
        fig.savefig(charts / (name + ".png"), dpi=170, bbox_inches="tight")
        fig.savefig(charts / (name + ".svg"), bbox_inches="tight")
        plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True, layout="constrained")
    for ax, sensor in zip(axes, ("MODIS", "VIIRS_SNPP")):
        values = {date.fromisocalendar(r["year"], r["week"], 1): r["count"] for r in rows if r["sensor"] == sensor}
        weeks, counts = [], []
        d = min(values)
        while d <= max(values):
            weeks.append(d)
            counts.append(values.get(d, float("nan")))
            d += timedelta(days=7)
        ax.plot(weeks, counts, color=colors[sensor], linewidth=.9, marker=".", markersize=1.6)
        ax.set_ylabel(sensor + "\nraw detections / week")
        ax.axvline(date(2023, 1, 1), color="#666666", linestyle=":", linewidth=1)
        ax.set_ylim(bottom=0)
    axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Kaduna | historical raw weekly detections\nStandard archives only; gaps are unknown, not zero. Dotted line: MODIS version-label transition (2023).", fontsize=12)
    save(fig, "raw_weekly_counts")

    pairs = comparison["pairs"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), layout="constrained")
    season_colors = {"DJF": "#b65b24", "MAM": "#2b876a", "JJA": "#376ead", "SON": "#8654a3"}
    for ax, era in zip(axes, ("version_6.03", "version_61.03")):
        sample = [p for p in pairs if p["modis_version_era"] == era]
        for season, color in season_colors.items():
            selected = [p for p in sample if p["season"] == season]
            ax.scatter([p["MODIS"] for p in selected], [p["VIIRS_SNPP"] for p in selected],
                       color=color, s=13, alpha=.6, label=season)
        top = max([p[s] for p in sample for s in ("MODIS", "VIIRS_SNPP")] or [1])
        ax.plot([1, top], [1, top], color="gray", linestyle="--", linewidth=.8, label="equal counts")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("MODIS raw detections (log axis)")
        ax.set_ylabel("VIIRS S-NPP raw detections (log axis)")
        ax.set_title(f"MODIS {era.replace('version_', '')} label era | n={len(sample)}")
    axes[0].legend(fontsize=8)
    fig.suptitle("Positive paired full ISO weeks | no fitted correction", fontsize=12)
    save(fig, "raw_paired_scatter")

    fig, ax = plt.subplots(figsize=(12, 5), layout="constrained")
    groups = [[p["VIIRS_SNPP"] / p["MODIS"] for p in pairs if p["month"] == m] for m in range(1, 13)]
    labels = [f"{name}\nn={len(group)}" for name, group in zip(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), groups)]
    ax.boxplot(groups, tick_labels=labels, showfliers=True,
               flierprops={"markersize": 2, "alpha": .35}, medianprops={"color": "#166980"})
    ax.set_yscale("log")
    ax.set_ylabel("Weekly VIIRS / MODIS raw count ratio (log axis)")
    ax.set_xlabel("Calendar month of ISO Thursday; empty groups have no positive paired weeks")
    ax.set_title("Kaduna | seasonality of unadjusted weekly ratios\nPositive-pair selection and small MODIS denominators can inflate ratios")
    save(fig, "raw_ratio_by_month")
    print("Charts written to " + str(charts))


if __name__ == "__main__":
    main()
