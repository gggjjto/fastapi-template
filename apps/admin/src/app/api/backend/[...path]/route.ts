import { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { backendFetch, passthrough, rejectCrossOrigin } from "@/lib/server-api";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  if (!["GET", "HEAD", "OPTIONS"].includes(request.method)) {
    const rejected = rejectCrossOrigin(request);
    if (rejected) return rejected;
  }

  const { path } = await context.params;
  if (
    !path.length ||
    !["health", "tenants"].includes(path[0]) ||
    path.some((part) => part === "." || part === ".." || part.includes("/") || part.includes("\\"))
  ) {
    return NextResponse.json({ code: "NOT_FOUND", message: "Unknown backend route", data: null }, { status: 404 });
  }
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer();
  const upstream = await backendFetch(
    `/api/v1/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`,
    { method: request.method, headers, body },
  );
  return passthrough(upstream);
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
