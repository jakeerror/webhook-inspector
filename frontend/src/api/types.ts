export interface Bin {
  id: string;
  created_at: string;
  expires_at: string;
  request_count: number;
  url?: string;
}

export interface CapturedRequestSummary {
  id: number;
  method: string;
  path: string;
  content_type: string | null;
  size_bytes: number;
  created_at: string;
}

export interface CapturedRequestDetail extends CapturedRequestSummary {
  bin_id: string;
  query: Record<string, string>;
  headers: Record<string, string>;
  body: string;
  body_truncated: boolean;
  source_ip: string;
}

export interface ReplayResult {
  status: number;
  duration_ms: number;
}

/** WebSocket event shapes (SPEC §4). */
export type LiveEvent =
  | { type: "connected"; bin_id: string }
  | { type: "request"; data: CapturedRequestSummary };
