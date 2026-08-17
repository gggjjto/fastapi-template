"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { PageState, useTenantId } from "@/components/admin-shell";
import { apiFetch, errorMessage, jsonRequest, type Page } from "@/lib/client-api";
import type { CrawlJob, CrawlTarget } from "@/lib/types";

type Handler = { name: string };

export default function TargetsPage() {
  const tenantId = useTenantId();
  const [targets, setTargets] = useState<CrawlTarget[]>([]);
  const [handlers, setHandlers] = useState<Handler[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    if (!tenantId) return { targets: [], handlers: [] };
    const base = `/api/backend/tenants/${tenantId}/crawler`;
    const [targetPage, handlerItems] = await Promise.all([
        apiFetch<Page<CrawlTarget>>(`${base}/targets?limit=100&offset=0`),
        apiFetch<Handler[]>(`${base}/handlers`),
    ]);
    return { targets: targetPage.items, handlers: handlerItems };
  }, [tenantId]);

  const load = useCallback(async () => {
    try {
      const data = await fetchData(); setTargets(data.targets); setHandlers(data.handlers); setError("");
    } catch (reason) { setError(errorMessage(reason)); }
    finally { setLoading(false); }
  }, [fetchData]);

  useEffect(() => {
    let active = true;
    fetchData()
      .then((data) => { if (active) { setTargets(data.targets); setHandlers(data.handlers); } })
      .catch((reason) => { if (active) setError(errorMessage(reason)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [fetchData]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const scheduleEnabled = form.get("schedule_enabled") === "on";
    try {
      await apiFetch(`/api/backend/tenants/${tenantId}/crawler/targets`, jsonRequest("POST", {
        name: form.get("name"),
        target_url: form.get("target_url"),
        handler_name: form.get("handler_name") || "http_snapshot",
        enabled: true,
        schedule_cron: form.get("schedule_cron") || null,
        schedule_timezone: form.get("schedule_timezone") || "UTC",
        schedule_enabled: scheduleEnabled,
      }));
      event.currentTarget.reset();
      await load();
    } catch (reason) { setError(errorMessage(reason)); }
  }

  async function toggle(target: CrawlTarget, field: "enabled" | "schedule_enabled") {
    try {
      await apiFetch(`/api/backend/tenants/${tenantId}/crawler/targets/${target.id}`, jsonRequest("PATCH", { [field]: !target[field] }));
      await load();
    } catch (reason) { setError(errorMessage(reason)); }
  }

  async function run(target: CrawlTarget) {
    if (!window.confirm(`Run ${target.name} now?`)) return;
    try {
      await apiFetch<CrawlJob>(`/api/backend/tenants/${tenantId}/crawler/targets/${target.id}/run`, jsonRequest("POST", {
        idempotency_key: `admin:${crypto.randomUUID()}`,
      }));
    } catch (reason) { setError(errorMessage(reason)); }
  }

  async function archive(target: CrawlTarget) {
    if (!window.confirm(`Archive ${target.name}? Its job history will remain available.`)) return;
    try {
      await apiFetch(`/api/backend/tenants/${tenantId}/crawler/targets/${target.id}/archive`, { method: "POST" });
      await load();
    } catch (reason) { setError(errorMessage(reason)); }
  }

  if (!tenantId) return <PageState empty="Select a tenant to manage crawler targets." />;
  return (
    <>
      <header className="page-header"><p className="eyebrow">Crawler</p><h2>Targets</h2></header>
      <PageState loading={loading} error={error} />
      <section className="panel">
        <h3>Add target</h3>
        <form className="form-grid" onSubmit={create}>
          <label>Name<input name="name" required maxLength={128} /></label>
          <label>URL<input name="target_url" type="url" required maxLength={2048} /></label>
          <label>Handler<select name="handler_name" defaultValue="http_snapshot">{(handlers.length ? handlers : [{ name: "http_snapshot" }]).map((handler) => <option key={handler.name}>{handler.name}</option>)}</select></label>
          <label>Cron<input name="schedule_cron" placeholder="0 * * * *" maxLength={128} /></label>
          <label>Timezone<input name="schedule_timezone" defaultValue="UTC" maxLength={64} /></label>
          <label className="check"><input name="schedule_enabled" type="checkbox" /> Enable schedule</label>
          <button className="primary">Create target</button>
        </form>
      </section>
      <section className="panel">
        <h3>Targets</h3>
        {!loading && targets.length === 0 ? <PageState empty="No crawler targets." /> : <div className="table-wrap"><table><thead><tr><th>Target</th><th>Handler</th><th>Schedule</th><th>State</th><th>Actions</th></tr></thead><tbody>
          {targets.map((target) => <tr key={target.id}><td><strong>{target.name}</strong><br /><span className="muted">{target.target_url}</span></td><td>{target.handler_name}</td><td>{target.schedule_cron ?? "Manual"}<br /><span className="muted">{target.schedule_timezone}</span></td><td>{target.enabled ? "enabled" : "disabled"} / {target.schedule_enabled ? "scheduled" : "manual"}</td><td><div className="button-row"><button onClick={() => run(target)}>Run</button><button onClick={() => toggle(target, "enabled")}>{target.enabled ? "Disable" : "Enable"}</button>{target.schedule_cron && <button onClick={() => toggle(target, "schedule_enabled")}>{target.schedule_enabled ? "Pause cron" : "Enable cron"}</button>}<button className="danger" onClick={() => archive(target)}>Archive</button></div></td></tr>)}
        </tbody></table></div>}
      </section>
    </>
  );
}
