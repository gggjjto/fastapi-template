"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageState, useTenantId } from "@/components/admin-shell";
import { apiFetch, errorMessage } from "@/lib/client-api";
import type { CrawlJob } from "@/lib/types";

const cancellable = new Set(["pending", "queued", "running", "retrying"]);
const retryable = new Set(["failed", "cancelled"]);

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const tenantId = useTenantId();
  const [job, setJob] = useState<CrawlJob | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!tenantId) return;
    let active = true;
    apiFetch<CrawlJob>(`/api/backend/tenants/${tenantId}/crawler/jobs/${id}`)
      .then((result) => { if (active) setJob(result); })
      .catch((reason) => { if (active) setError(errorMessage(reason)); });
    return () => { active = false; };
  }, [id, tenantId]);

  async function action(name: "cancel" | "retry") {
    if (!job || !window.confirm(`${name === "cancel" ? "Cancel" : "Retry"} this job?`)) return;
    try {
      const result = await apiFetch<CrawlJob>(`/api/backend/tenants/${tenantId}/crawler/jobs/${id}/${name}`, { method: "POST" });
      if (name === "retry") router.push(`/crawler/jobs/${result.id}?tenant=${tenantId}`);
      else setJob(result);
    } catch (reason) { setError(errorMessage(reason)); }
  }

  if (!tenantId) return <PageState empty="Select a tenant to view this job." />;
  if (!job) return <PageState loading={!error} error={error} />;
  return (
    <>
      <header className="page-header"><p className="eyebrow">Crawler job</p><h2>{job.id}</h2><div className="button-row">{cancellable.has(job.status) && <button className="danger" onClick={() => action("cancel")}>Cancel</button>}{retryable.has(job.status) && <button className="primary" onClick={() => action("retry")}>Retry</button>}</div></header>
      {error && <PageState error={error} />}
      <section className="card-grid">
        {[['Status', job.status], ['Dispatch', job.dispatch_state], ['Attempts', String(job.attempt_count)], ['Target', job.crawl_target_id]].map(([label, value]) => <article className="card" key={label}><p className="eyebrow">{label}</p><strong>{value}</strong></article>)}
      </section>
      <section className="panel"><h3>Timeline</h3><dl className="details"><dt>Created</dt><dd>{new Date(job.created_at).toLocaleString()}</dd><dt>Dispatched</dt><dd>{job.dispatched_at ? new Date(job.dispatched_at).toLocaleString() : "—"}</dd><dt>Started</dt><dd>{job.started_at ? new Date(job.started_at).toLocaleString() : "—"}</dd><dt>Finished</dt><dd>{job.finished_at ? new Date(job.finished_at).toLocaleString() : "—"}</dd></dl></section>
      {job.error_message && <section className="panel error-panel"><h3>Error</h3><pre>{job.error_message}</pre></section>}
      <section className="panel"><h3>Result</h3>{job.result ? <pre>{JSON.stringify(job.result, null, 2)}</pre> : <PageState empty="No result has been recorded." />}</section>
    </>
  );
}
