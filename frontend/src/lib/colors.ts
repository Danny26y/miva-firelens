import type { ScaleMode } from "./types";

/** FIRMS-like thermal ramp: cool charcoal → amber → orange → hot white. */
const RAMP = [
  [26, 18, 8],
  [92, 42, 10],
  [166, 58, 8],
  [220, 90, 18],
  [240, 150, 40],
  [255, 210, 110],
  [255, 245, 214],
] as const;

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function sampleRamp(t: number): string {
  const x = Math.min(1, Math.max(0, t));
  const scaled = x * (RAMP.length - 1);
  const i = Math.floor(scaled);
  const f = scaled - i;
  const c0 = RAMP[i];
  const c1 = RAMP[Math.min(RAMP.length - 1, i + 1)];
  const r = Math.round(lerp(c0[0], c1[0], f));
  const g = Math.round(lerp(c0[1], c1[1], f));
  const b = Math.round(lerp(c0[2], c1[2], f));
  return `rgb(${r}, ${g}, ${b})`;
}

export function fireColor(
  count: number | null,
  max: number,
  scale: ScaleMode,
): string {
  if (count === null || max <= 0) return "var(--gap)";
  if (count <= 0) return "var(--gap)";
  let t: number;
  if (scale === "log") {
    t = Math.log1p(count) / Math.log1p(max);
  } else {
    t = count / max;
  }
  return sampleRamp(Math.pow(t, 0.85));
}

export function legendStops(max: number, scale: ScaleMode): { label: string; color: string }[] {
  const fractions = [0.05, 0.2, 0.4, 0.65, 1];
  return fractions.map((f) => {
    let value: number;
    if (scale === "log") {
      value = Math.round(Math.expm1(f * Math.log1p(max)));
    } else {
      value = Math.round(f * max);
    }
    return {
      label: value.toLocaleString(),
      color: fireColor(Math.max(1, value), max, scale),
    };
  });
}
