"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { apiFetch, errorMessage, type Page } from "@/lib/client-api";
import type { Tenant, User } from "@/lib/types";

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [user, setUser] = useState<User | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState("");
  const tenantId = searchParams.get("tenant") ?? "";

  useEffect(() => {
    Promise.all([
      apiFetch<User>("/api/auth/me"),
      apiFetch<Page<Tenant>>("/api/backend/tenants?limit=100&offset=0"),
    ])
      .then(([me, page]) => {
        setUser(me);
        setTenants(page.items);
      })
      .catch((reason) => {
        if (reason?.status === 401) router.replace("/login");
        else setError(errorMessage(reason));
      });
  }, [router]);

  function changeTenant(nextTenant: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (nextTenant) params.set("tenant", nextTenant);
    else params.delete("tenant");
    router.push(`${pathname}?${params.toString()}`);
  }

  async function logout(path: "/api/auth/logout" | "/api/auth/logout-all") {
    if (path.endsWith("logout-all") && !window.confirm("Sign out every active session?")) return;
    await apiFetch<unknown>(path, { method: "POST" }).catch(() => null);
    router.replace("/login");
  }

  const query = tenantId ? `?tenant=${tenantId}` : "";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Rapid Development</p>
          <h1>Admin</h1>
        </div>
        <nav aria-label="Primary navigation">
          <Link href={`/${query}`}>Overview</Link>
          <Link href={`/tenants${query}`}>Tenants</Link>
          <Link href={`/crawler/targets${query}`}>Crawler targets</Link>
          <Link href={`/crawler/jobs${query}`}>Crawler jobs</Link>
        </nav>
        <div className="sidebar-footer">
          <label>
            Tenant
            <select value={tenantId} onChange={(event) => changeTenant(event.target.value)}>
              <option value="">Select tenant</option>
              {tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>{tenant.name}</option>
              ))}
            </select>
          </label>
          {user && <p className="muted">{user.full_name}<br />{user.email}</p>}
          {error && <p className="error">{error}</p>}
          <div className="button-row">
            <button onClick={() => logout("/api/auth/logout")}>Sign out</button>
            <button className="ghost" onClick={() => logout("/api/auth/logout-all")}>All sessions</button>
          </div>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}

export function useTenantId(): string {
  return useSearchParams().get("tenant") ?? "";
}

export function PageState({ loading, error, empty }: { loading?: boolean; error?: string; empty?: string }) {
  if (loading) return <p className="state">Loading…</p>;
  if (error) return <p className="state error">{error}</p>;
  if (empty) return <p className="state">{empty}</p>;
  return null;
}
