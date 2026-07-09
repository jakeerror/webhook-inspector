import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";

import { ApiError, ingestUrl } from "../api/client";
import { binsApi } from "../api/endpoints";
import type { ReplayResult } from "../api/types";
import { useLiveRequests } from "../hooks/useLiveRequests";

export function BinPage() {
  const { id = "" } = useParams();
  const { requests, connected } = useLiveRequests(id);
  const [selected, setSelected] = useState<number | null>(null);

  const bin = useQuery({ queryKey: ["bin", id], queryFn: () => binsApi.get(id) });

  if (bin.isError) {
    return (
      <div className="center">
        <div className="card">
          <p className="error">Bin не найден или истёк.</p>
          <Link to="/">← на главную</Link>
        </div>
      </div>
    );
  }

  const url = ingestUrl(id);

  return (
    <div className="binpage">
      <header className="topbar">
        <Link to="/" className="brand">
          Webhook Inspector
        </Link>
        <code className="ingest-url" onClick={() => navigator.clipboard.writeText(url)} title="Скопировать">
          {url}
        </code>
        <span className={`dot ${connected ? "on" : "off"}`} title={connected ? "live" : "offline"} />
        <div className="spacer" />
        <span className="muted small">
          {requests.length} запросов · истекает {bin.data ? new Date(bin.data.expires_at).toLocaleDateString() : "…"}
        </span>
      </header>

      <div className="split">
        <div className="req-list">
          {requests.length === 0 && (
            <p className="muted empty">
              Ожидаем запросы… отправь что-нибудь на URL выше:
              <br />
              <code>curl -X POST {url} -d &apos;hello&apos;</code>
            </p>
          )}
          {requests.map((r) => (
            <button
              key={r.id}
              className={`req-item ${selected === r.id ? "active" : ""}`}
              onClick={() => setSelected(r.id)}
            >
              <span className={`method m-${r.method.toLowerCase()}`}>{r.method}</span>
              <span className="req-path">/{r.path}</span>
              <span className="muted small">{new Date(r.created_at).toLocaleTimeString()}</span>
            </button>
          ))}
        </div>

        <div className="req-detail">
          {selected === null ? (
            <p className="muted empty">Выбери запрос слева</p>
          ) : (
            <RequestDetail binId={id} requestId={selected} />
          )}
        </div>
      </div>
    </div>
  );
}

function RequestDetail({ binId, requestId }: { binId: string; requestId: number }) {
  const detail = useQuery({
    queryKey: ["request", binId, requestId],
    queryFn: () => binsApi.request(binId, requestId),
  });
  const [target, setTarget] = useState("");
  const [result, setResult] = useState<ReplayResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const replay = useMutation({
    mutationFn: () => binsApi.replay(binId, requestId, target),
    onSuccess: (r) => {
      setResult(r);
      setError(null);
    },
    onError: (e) => {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Ошибка");
    },
  });

  if (!detail.data) return <p className="muted">Загрузка…</p>;
  const d = detail.data;

  return (
    <div>
      <h3>
        <span className={`method m-${d.method.toLowerCase()}`}>{d.method}</span> /{d.path}
      </h3>
      <p className="muted small">
        от {d.source_ip} · {d.size_bytes} байт{d.body_truncated ? " (усечено)" : ""}
      </p>

      <Section title="Query">
        <KeyVals data={d.query} />
      </Section>
      <Section title="Заголовки">
        <KeyVals data={d.headers} />
      </Section>
      <Section title="Тело">
        <pre className="body">{prettify(d.body, d.content_type)}</pre>
      </Section>

      <Section title="Replay">
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (target.trim()) replay.mutate();
          }}
        >
          <input
            placeholder="https://your-app.example/webhook"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
          />
          <button className="primary" type="submit" disabled={replay.isPending}>
            Переслать
          </button>
        </form>
        {result && (
          <p className="ok small">
            Отправлено → HTTP {result.status} за {result.duration_ms} мс
          </p>
        )}
        {error && <p className="error small">{error}</p>}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="section">
      <h4>{title}</h4>
      {children}
    </div>
  );
}

function KeyVals({ data }: { data: Record<string, string> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return <p className="muted small">—</p>;
  return (
    <table className="kv">
      <tbody>
        {entries.map(([k, v]) => (
          <tr key={k}>
            <td className="k">{k}</td>
            <td className="v">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function prettify(body: string, contentType: string | null): string {
  if (!body) return "(пусто)";
  if (contentType && contentType.includes("json")) {
    try {
      return JSON.stringify(JSON.parse(body), null, 2);
    } catch {
      return body;
    }
  }
  return body;
}
