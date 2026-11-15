import type { Comparison, PairedWeek, Provenance, WeeklyRecord } from "./types";

async function loadJson<T>(name: string, signal?: AbortSignal): Promise<T> {
  const base = import.meta.env.BASE_URL;
  const response = await fetch(`${base}data/${name}.json`, { signal });
  if (!response.ok) {
    throw new Error(`Failed to load ${name}.json (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export type FireLensData = {
  weeks: WeeklyRecord[];
  provenance: Provenance;
  comparison: Comparison;
  pairs: PairedWeek[];
};

export async function loadFireLensData(
  signal?: AbortSignal,
): Promise<FireLensData> {
  const [weeks, provenance, comparison, pairs] = await Promise.all([
    loadJson<WeeklyRecord[]>("weekly_fire_counts", signal),
    loadJson<Provenance>("provenance", signal),
    loadJson<Comparison>("comparison", signal),
    loadJson<PairedWeek[]>("paired_weeks", signal),
  ]);
  return { weeks, provenance, comparison, pairs };
}
