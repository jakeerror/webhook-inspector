import { apiFetch } from "./client";
import type {
  Bin,
  CapturedRequestDetail,
  CapturedRequestSummary,
  ReplayResult,
} from "./types";

export const binsApi = {
  create: () => apiFetch<Bin>("/api/v1/bins", { method: "POST" }),
  get: (id: string) => apiFetch<Bin>(`/api/v1/bins/${id}`),
  remove: (id: string) => apiFetch<void>(`/api/v1/bins/${id}`, { method: "DELETE" }),
  requests: (id: string) =>
    apiFetch<CapturedRequestSummary[]>(`/api/v1/bins/${id}/requests?limit=100`),
  request: (id: string, rid: number) =>
    apiFetch<CapturedRequestDetail>(`/api/v1/bins/${id}/requests/${rid}`),
  replay: (id: string, rid: number, targetUrl: string) =>
    apiFetch<ReplayResult>(`/api/v1/bins/${id}/requests/${rid}/replay`, {
      method: "POST",
      body: { target_url: targetUrl },
    }),
};
