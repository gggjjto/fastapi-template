import { backendFetch, passthrough } from "@/lib/server-api";

export async function GET() {
  return passthrough(await backendFetch("/api/v1/auth/me"));
}
