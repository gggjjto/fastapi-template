"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { apiFetch, errorMessage, jsonRequest } from "@/lib/client-api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await apiFetch("/api/auth/login", jsonRequest("POST", {
        email: form.get("email"),
        password: form.get("password"),
      }));
      router.replace("/");
    } catch (reason) {
      setError(errorMessage(reason));
      setPending(false);
    }
  }

  return (
    <main className="login-page">
      <form className="panel login-panel" onSubmit={submit}>
        <p className="eyebrow">Rapid Development</p>
        <h1>Admin sign in</h1>
        <label>Email<input name="email" type="email" autoComplete="username" required /></label>
        <label>Password<input name="password" type="password" autoComplete="current-password" minLength={8} required /></label>
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={pending}>{pending ? "Signing in…" : "Sign in"}</button>
      </form>
    </main>
  );
}
