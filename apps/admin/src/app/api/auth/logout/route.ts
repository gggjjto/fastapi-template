import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

import {
  apiBaseUrl,
  clearTokenCookies,
  refreshCookie,
  rejectCrossOrigin,
} from "@/lib/server-api";

export async function POST(request: NextRequest) {
  const rejected = rejectCrossOrigin(request);
  if (rejected) return rejected;

  const refreshToken = (await cookies()).get(refreshCookie)?.value;
  try {
    if (refreshToken) {
      await fetch(`${apiBaseUrl}/api/v1/auth/logout`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
        cache: "no-store",
      });
    }
  } finally {
    await clearTokenCookies();
  }
  return NextResponse.json({ code: "OK", message: "logged out", data: null });
}
