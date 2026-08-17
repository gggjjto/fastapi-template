"use client";

import { useEffect, useState } from "react";

import { PageState } from "@/components/admin-shell";
import { apiFetch, errorMessage } from "@/lib/client-api";

type Health = Record<string, string>;

export default function OverviewPage() {
  const [live, setLive] = useState<Health | null>(null);
  const [ready, setReady] = useState<Health | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiFetch<Health>("/api/backend/health/live"),
      apiFetch<Health>("/api/backend/health/ready"),
    ])
      .then(([liveResult, readyResult]) => {
        setLive(liveResult);
        setReady(readyResult);
      })
      .catch((reason) => setError(errorMessage(reason)));
  }, []);

  return (
    <>
      <header className="page-header">
        <p className="eyebrow">System</p>
        <h2>Health overview</h2>
        <p>Live checks from the API, not hardcoded workspace labels.</p>
      </header>
      <PageState loading={!live && !error} error={error} />
      {live && ready && (
        <section className="card-grid">
          {[...Object.entries(live), ...Object.entries(ready)].map(([name, value], index) => (
            <article className="card" key={`${name}-${index}`}>
              <p className="eyebrow">{name}</p>
              <strong>{value}</strong>
            </article>
          ))}
          {!["worker", "dispatcher", "scheduler"].some((key) => key in ready) && (
            <article className="card muted-card">
              <p className="eyebrow">Background services</p>
              <strong>Not reported</strong>
              <p className="muted">The API health contract does not expose worker state yet.</p>
            </article>
          )}
        </section>
      )}
    </>
  );
}
