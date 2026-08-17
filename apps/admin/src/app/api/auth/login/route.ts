import { NextRequest, NextResponse } from "next/server";

import { apiBaseUrl, rejectCrossOrigin, setTokenCookies } from "@/lib/server-api";

export async function POST(request: NextRequest) {
  const rejected = rejectCrossOrigin(request);
  if (rejected) return rejected;

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/api/v1/auth/token`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: await request.text(),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { code: "API_UNAVAILABLE", message: "Authentication service unavailable", data: null },
      { status: 502 },
    );
  }
  const payload = await response.json().catch(() => ({
    code: "INVALID_API_RESPONSE", message: "Authentication service returned an invalid response", data: null,
  })) as { code?: string; message?: string; request_id?: string | null; data?: { access_token?: string; refresh_token?: string } | null };
  const accessToken = payload.data?.access_token;
  const refreshToken = payload.data?.refresh_token;
  if (response.ok) {
    if (!accessToken || !refreshToken) {
      return NextResponse.json(
        { code: "INVALID_API_RESPONSE", message: "Authentication service returned an invalid response", data: null },
        { status: 502 },
      );
    }
    await setTokenCookies(accessToken, refreshToken);
    return NextResponse.json({ ...payload, data: { authenticated: true } }, { status: response.status });
  }
  return NextResponse.json(
    {
      code: payload.code ?? "AUTHENTICATION_FAILED",
      message: payload.message ?? "Authentication failed",
      request_id: payload.request_id ?? null,
      data: null,
    },
    { status: response.status },
  );
}
