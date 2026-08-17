import { Suspense } from "react";

import { AdminShell } from "@/components/admin-shell";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<p className="state">Loading admin…</p>}>
      <AdminShell>{children}</AdminShell>
    </Suspense>
  );
}
