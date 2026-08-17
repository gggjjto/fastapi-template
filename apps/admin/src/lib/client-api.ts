export type ApiEnvelope<T> = {
  code: string;
  message: string;
  data: T | null;
  request_id?: string | null;
};

export type Page<T> = { items: T[]; total: number; limit: number; offset: number };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, cache: "no-store" });
  const payload = (await response.json().catch(() => null)) as ApiEnvelope<T> | null;
  if (!response.ok || !payload || payload.data === null) {
    throw new ApiError(payload?.message ?? "Request failed", response.status, payload?.code);
  }
  return payload.data;
}

export function jsonRequest(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: body === undefined ? undefined : { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) return "You do not have permission for this action.";
  return error instanceof Error ? error.message : "Something went wrong.";
}
