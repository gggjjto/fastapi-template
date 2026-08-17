import { NextRequest } from "next/server";

import {
  backendFetch,
  clearTokenCookies,
  passthrough,
  rejectCrossOrigin,
} from "@/lib/server-api";

export async function POST(request: NextRequest) {
  const rejected = rejectCrossOrigin(request);
  if (rejected) return rejected;

  try {
    return passthrough(await backendFetch("/api/v1/auth/logout-all", { method: "POST" }));
  } finally {
    await clearTokenCookies();
  }
}
