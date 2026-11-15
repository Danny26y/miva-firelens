import { useEffect, useMemo, useState } from "react";
import { AppShell, type AppPage } from "./components/AppShell";
import { CalendarPage } from "./components/CalendarPage";
import { PlaceholderPage } from "./components/PlaceholderPage";
import { SeasonPage } from "./components/SeasonPage";
import { buildIndex } from "./lib/calendar";
import { loadFireLensData, type FireLensData } from "./lib/data";

export default function App() {
  const [data, setData] = useState<FireLensData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<AppPage>("calendar");

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

  if (error) {
    return (
      <div className="app-shell">
        <div className="status-banner error">{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="app-shell">
        <div className="status-banner">Loading Kaduna weekly detections…</div>
      </div>
    );
  }

  return (
    <AppShell page={page} onNavigate={setPage}>
      {page === "calendar" && (
        <CalendarPage
          weeks={data.weeks}
          provenance={data.provenance}
          index={index}
          onOpenSeason={() => setPage("season")}
        />
      )}
      {page === "season" && (
        <SeasonPage weeks={data.weeks} provenance={data.provenance} />
      )}
      {page === "overview" && (
        <PlaceholderPage
          title="Fire season overview"
          body="Overview KPIs and national walkthrough from the Figma board will plug in here next."
        />
      )}
      {page === "map" && (
        <PlaceholderPage
          title="Fire map"
          body="The historical fire map screen from Figma is not connected yet — calendar remains the primary analysis surface."
        />
      )}
      {page === "about" && (
        <PlaceholderPage
          title="About the data"
          body={`${data.provenance.limitations.join(" ")} Boundary: ${data.provenance.boundary.source} (${data.provenance.boundary.license}).`}
        />
      )}
    </AppShell>
  );
}
