"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { PageState, useTenantId } from "@/components/admin-shell";
import { apiFetch, errorMessage, jsonRequest, type Page } from "@/lib/client-api";
import type { Tenant, TenantInvitation, TenantMember } from "@/lib/types";

export default function TenantsPage() {
  const tenantId = useTenantId();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [members, setMembers] = useState<TenantMember[]>([]);
  const [invitations, setInvitations] = useState<TenantInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    const tenantPage = await apiFetch<Page<Tenant>>("/api/backend/tenants?limit=100&offset=0");
    if (tenantId) {
      const [memberPage, invitationPage] = await Promise.all([
          apiFetch<Page<TenantMember>>(`/api/backend/tenants/${tenantId}/members?limit=100&offset=0`),
          apiFetch<Page<TenantInvitation>>(`/api/backend/tenants/${tenantId}/invitations?limit=100&offset=0`),
      ]);
      return { tenants: tenantPage.items, members: memberPage.items, invitations: invitationPage.items };
    }
    return { tenants: tenantPage.items, members: [], invitations: [] };
  }, [tenantId]);

  const load = useCallback(async () => {
    try {
      const data = await fetchData();
      setTenants(data.tenants); setMembers(data.members); setInvitations(data.invitations); setError("");
    } catch (reason) { setError(errorMessage(reason)); }
    finally { setLoading(false); }
  }, [fetchData]);

  useEffect(() => {
    let active = true;
    fetchData()
      .then((data) => { if (active) { setTenants(data.tenants); setMembers(data.members); setInvitations(data.invitations); } })
      .catch((reason) => { if (active) setError(errorMessage(reason)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [fetchData]);

  async function createTenant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await apiFetch<Tenant>("/api/backend/tenants", jsonRequest("POST", {
        name: form.get("name"), slug: form.get("slug"), owner_email: form.get("owner_email"),
      }));
      event.currentTarget.reset();
      await load();
    } catch (reason) { setError(errorMessage(reason)); }
  }

  async function invite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await apiFetch<TenantInvitation>(`/api/backend/tenants/${tenantId}/invitations`, jsonRequest("POST", {
        email: form.get("email"), role: form.get("role"),
      }));
      event.currentTarget.reset();
      await load();
    } catch (reason) { setError(errorMessage(reason)); }
  }

  async function updateRole(userId: string, role: string) {
    try {
      await apiFetch(`/api/backend/tenants/${tenantId}/members/${userId}`, jsonRequest("PATCH", { role }));
      await load();
    } catch (reason) { setError(errorMessage(reason)); }
  }

  async function removeMember(member: TenantMember) {
    if (!window.confirm(`Remove ${member.email} from this tenant?`)) return;
    try {
      await apiFetch(`/api/backend/tenants/${tenantId}/members/${member.user_id}`, { method: "DELETE" });
      await load();
    } catch (reason) { setError(errorMessage(reason)); }
  }

  async function revokeInvitation(invitation: TenantInvitation) {
    if (!window.confirm(`Revoke the invitation for ${invitation.email}?`)) return;
    try {
      await apiFetch(`/api/backend/tenants/${tenantId}/invitations/${invitation.id}/revoke`, { method: "POST" });
      await load();
    } catch (reason) { setError(errorMessage(reason)); }
  }

  return (
    <>
      <header className="page-header"><p className="eyebrow">Access</p><h2>Tenants and members</h2></header>
      <PageState loading={loading} error={error} empty={!loading && tenants.length === 0 ? "No tenants are available." : undefined} />
      <section className="panel">
        <h3>Create tenant</h3>
        <form className="form-grid" onSubmit={createTenant}>
          <label>Name<input name="name" required maxLength={255} /></label>
          <label>Slug<input name="slug" required minLength={2} maxLength={63} pattern="[a-z0-9]+(?:-[a-z0-9]+)*" /></label>
          <label>Owner email<input name="owner_email" type="email" required /></label>
          <button className="primary">Create and invite owner</button>
        </form>
      </section>
      <section className="panel">
        <h3>Available tenants</h3>
        <div className="table-wrap"><table><thead><tr><th>Name</th><th>Slug</th><th>Status</th></tr></thead><tbody>
          {tenants.map((tenant) => <tr key={tenant.id}><td>{tenant.name}</td><td>{tenant.slug}</td><td><span className="badge">{tenant.status}</span></td></tr>)}
        </tbody></table></div>
      </section>
      {!tenantId ? <PageState empty="Select a tenant to manage its members and invitations." /> : (
        <>
          <section className="panel">
            <div className="section-heading"><h3>Members</h3></div>
            {members.length === 0 ? <PageState empty="No members found." /> : <div className="table-wrap"><table><thead><tr><th>User</th><th>Role</th><th>Action</th></tr></thead><tbody>
              {members.map((member) => <tr key={member.user_id}><td>{member.full_name}<br /><span className="muted">{member.email}</span></td><td><select value={member.role} onChange={(event) => updateRole(member.user_id, event.target.value)}><option value="owner">owner</option><option value="admin">admin</option><option value="member">member</option></select></td><td><button className="danger" onClick={() => removeMember(member)}>Remove</button></td></tr>)}
            </tbody></table></div>}
          </section>
          <section className="panel">
            <h3>Invite member</h3>
            <form className="form-grid compact" onSubmit={invite}>
              <label>Email<input name="email" type="email" required /></label>
              <label>Role<select name="role" defaultValue="member"><option value="owner">owner</option><option value="admin">admin</option><option value="member">member</option></select></label>
              <button className="primary">Send invitation</button>
            </form>
            {invitations.length === 0 ? <PageState empty="No invitations." /> : <div className="table-wrap"><table><thead><tr><th>Email</th><th>Role</th><th>Status</th><th>Action</th></tr></thead><tbody>
              {invitations.map((item) => <tr key={item.id}><td>{item.email}</td><td>{item.role}</td><td>{item.accepted_at ? "accepted" : item.revoked_at ? "revoked" : "pending"}</td><td>{!item.accepted_at && !item.revoked_at && <button className="danger" onClick={() => revokeInvitation(item)}>Revoke</button>}</td></tr>)}
            </tbody></table></div>}
          </section>
        </>
      )}
    </>
  );
}
