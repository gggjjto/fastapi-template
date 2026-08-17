import { NextRequest } from "next/server";

import { backendFetch, passthrough, rejectCrossOrigin } from "@/lib/server-api";

export async function POST(request: NextRequest) {
  const rejected = rejectCrossOrigin(request);
  if (rejected) return rejected;
  return passthrough(await backendFetch("/api/v1/tenant-invitations/accept", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  }));
}
