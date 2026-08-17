"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { apiFetch, errorMessage, jsonRequest } from "@/lib/client-api";

function InvitationForm() {
  const searchParams = useSearchParams();
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await apiFetch("/api/invitations/accept", jsonRequest("POST", {
        token: form.get("token"),
        email: form.get("email"),
        full_name: form.get("full_name") || null,
        password: form.get("password") || null,
      }));
      setAccepted(true);
    } catch (reason) { setError(errorMessage(reason)); }
  }

  if (accepted) return <section className="panel login-panel"><h1>Invitation accepted</h1><p>You can now access the tenant.</p><Link href="/login">Continue to sign in</Link></section>;
  return (
    <form className="panel login-panel" onSubmit={submit}>
      <p className="eyebrow">Tenant invitation</p><h1>Join the workspace</h1>
      <label>Invitation token<input name="token" defaultValue={searchParams.get("token") ?? ""} minLength={20} required /></label>
      <label>Email<input name="email" type="email" defaultValue={searchParams.get("email") ?? ""} required /></label>
      <p className="muted">Already have an account? Sign in first, then return to this invitation. New users must set a name and password below.</p>
      <label>Full name<input name="full_name" maxLength={255} /></label>
      <label>Password<input name="password" type="password" minLength={8} maxLength={128} autoComplete="new-password" /></label>
      {error && <p className="error">{error}</p>}
      <button className="primary">Accept invitation</button>
      <Link href="/login">Sign in</Link>
    </form>
  );
}

export default function AcceptInvitationPage() {
  return <main className="login-page"><Suspense fallback={<p>Loading invitation…</p>}><InvitationForm /></Suspense></main>;
}
