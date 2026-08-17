import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { createHash } from "node:crypto";

import { cookieOptions, isSameOrigin } from "./request-security";

const apiBaseUrl = (process.env.API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const accessCookie = "rapid_access_token";
const refreshCookie = "rapid_refresh_token";

type TokenEnvelope = {
  data?: { access_token?: string; refresh_token?: string };
};

type TokenPair = { accessToken: string; refreshToken: string };
const refreshRequests = new Map<string, Promise<TokenPair | null>>();

export function rejectCrossOrigin(request: NextRequest): NextResponse | null {
  if (!isSameOrigin(request.url, request.headers.get("origin"))) {
    return NextResponse.json(
      { code: "INVALID_ORIGIN", message: "Cross-origin mutation rejected", data: null },
      { status: 403 },
    );
  }
  return null;
}

export async function setTokenCookies(accessToken: string, refreshToken: string): Promise<void> {
  const store = await cookies();
  store.set(accessCookie, accessToken, { ...cookieOptions, maxAge: 30 * 60 });
  store.set(refreshCookie, refreshToken, { ...cookieOptions, maxAge: 30 * 24 * 60 * 60 });
}

export async function clearTokenCookies(): Promise<void> {
  const store = await cookies();
  store.set(accessCookie, "", { ...cookieOptions, maxAge: 0 });
  store.set(refreshCookie, "", { ...cookieOptions, maxAge: 0 });
}

async function refreshTokens(): Promise<boolean> {
  const store = await cookies();
  const refreshToken = store.get(refreshCookie)?.value;
  if (!refreshToken) return false;

  const key = createHash("sha256").update(refreshToken).digest("hex");
  let refreshRequest = refreshRequests.get(key);
  if (!refreshRequest) {
    refreshRequest = fetch(`${apiBaseUrl}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    }).then(async (response) => {
      if (!response.ok) return null;
      const payload = (await response.json()) as TokenEnvelope;
      const accessToken = payload.data?.access_token;
      const nextRefreshToken = payload.data?.refresh_token;
      return accessToken && nextRefreshToken
        ? { accessToken, refreshToken: nextRefreshToken }
        : null;
    });
    refreshRequests.set(key, refreshRequest);
    setTimeout(() => refreshRequests.delete(key), 5_000);
  }

  const tokens = await refreshRequest;
  if (!tokens) {
    await clearTokenCookies();
    return false;
  }
  await setTokenCookies(tokens.accessToken, tokens.refreshToken);
  return true;
}

export async function backendFetch(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<Response> {
  const store = await cookies();
  const headers = new Headers(init.headers);
  const accessToken = store.get(accessCookie)?.value;
  if (accessToken) headers.set("authorization", `Bearer ${accessToken}`);

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (response.status === 401 && retry && (await refreshTokens())) {
    return backendFetch(path, init, false);
  }
  return response;
}

export async function passthrough(response: Response): Promise<NextResponse> {
  const headers = new Headers();
  const contentType = response.headers.get("content-type");
  const requestId = response.headers.get("x-request-id");
  if (contentType) headers.set("content-type", contentType);
  if (requestId) headers.set("x-request-id", requestId);
  return new NextResponse(await response.arrayBuffer(), { status: response.status, headers });
}

export { accessCookie, apiBaseUrl, refreshCookie };
