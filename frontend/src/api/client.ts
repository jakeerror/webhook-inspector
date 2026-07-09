const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
}

export async function apiFetch<T>(
  path: string,
  { method = "GET", body }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data: unknown = text ? JSON.parse(text) : undefined;

  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : res.statusText;
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

/** Build the WebSocket URL for a bin's live stream from the HTTP base. */
export function wsUrl(binId: string): string {
  const url = new URL(`${BASE_URL}/ws/bins/${binId}`);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function ingestUrl(binId: string): string {
  return `${BASE_URL}/in/${binId}`;
}
