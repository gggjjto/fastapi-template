"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { PageState, useTenantId } from "@/components/admin-shell";
import { apiFetch, errorMessage, type Page } from "@/lib/client-api";
import type { CrawlJob } from "@/lib/types";

export default function JobsPage() {
  const tenantId = useTenantId();
  const [jobs, setJobs] = useState<CrawlJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchJobs = useCallback(async (filters = "") => {
    if (!tenantId) return [];
    const suffix = filters ? `&${filters}` : "";
    const page = await apiFetch<Page<CrawlJob>>(`/api/backend/tenants/${tenantId}/crawler/jobs?limit=100&offset=0${suffix}`);
    return page.items;
  }, [tenantId]);

  async function load(filters = "") {
    try {
      setJobs(await fetchJobs(filters)); setError("");
    } catch (reason) { setError(errorMessage(reason)); }
    finally { setLoading(false); }
  }

  useEffect(() => {
    let active = true;
    fetchJobs()
      .then((items) => { if (active) setJobs(items); })
      .catch((reason) => { if (active) setError(errorMessage(reason)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [fetchJobs]);

  function filter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const params = new URLSearchParams();
    for (const name of ["status", "handler_name", "target_id", "created_from", "created_to"]) {
      const value = String(form.get(name) ?? "");
      if (value) params.set(name, name.startsWith("created_") ? new Date(value).toISOString() : value);
    }
    const next = params.toString();
    void load(next);
  }

  if (!tenantId) return <PageState empty="Select a tenant to view crawler jobs." />;
  return (
    <>
      <header className="page-header"><p className="eyebrow">Crawler</p><h2>Jobs</h2></header>
      <section className="panel">
        <form className="filter-row" onSubmit={filter}>
          <label>Status<select name="status" defaultValue=""><option value="">All</option>{["pending", "queued", "running", "retrying", "succeeded", "failed", "cancelled"].map((status) => <option key={status}>{status}</option>)}</select></label>
          <label>Handler<input name="handler_name" /></label>
          <label>Target ID<input name="target_id" /></label>
          <label>From<input name="created_from" type="datetime-local" /></label>
          <label>To<input name="created_to" type="datetime-local" /></label>
          <button className="primary">Filter</button>
        </form>
      </section>
      <PageState loading={loading} error={error} empty={!loading && jobs.length === 0 ? "No jobs match these filters." : undefined} />
      {jobs.length > 0 && <section className="panel"><div className="table-wrap"><table><thead><tr><th>Job</th><th>Status</th><th>Dispatch</th><th>Attempts</th><th>Created</th></tr></thead><tbody>
        {jobs.map((job) => <tr key={job.id}><td><Link href={`/crawler/jobs/${job.id}?tenant=${tenantId}`}>{job.id.slice(0, 8)}</Link><br /><span className="muted">{job.crawl_target_id.slice(0, 8)}</span></td><td><span className={`badge status-${job.status}`}>{job.status}</span></td><td>{job.dispatch_state}</td><td>{job.attempt_count}</td><td>{new Date(job.created_at).toLocaleString()}</td></tr>)}
      </tbody></table></div></section>}
    </>
  );
}
