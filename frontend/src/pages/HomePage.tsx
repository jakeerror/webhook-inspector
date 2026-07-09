import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { ApiError } from "../api/client";
import { binsApi } from "../api/endpoints";

export function HomePage() {
  const navigate = useNavigate();
  const [existing, setExisting] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => binsApi.create(),
    onSuccess: (bin) => navigate(`/b/${bin.id}`),
    onError: (e) => setError(e instanceof ApiError ? e.message : "Ошибка"),
  });

  return (
    <div className="center">
      <div className="card hero">
        <h1>Webhook Inspector</h1>
        <p className="muted">
          Создай временный endpoint, направь на него вебхуки и смотри входящие
          запросы в реальном времени.
        </p>
        <button
          className="primary big"
          onClick={() => create.mutate()}
          disabled={create.isPending}
        >
          {create.isPending ? "Создаём…" : "Создать endpoint"}
        </button>
        {error && <p className="error">{error}</p>}

        <div className="divider">или открыть существующий</div>
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (existing.trim()) navigate(`/b/${existing.trim()}`);
          }}
        >
          <input
            placeholder="bin id"
            value={existing}
            onChange={(e) => setExisting(e.target.value)}
          />
          <button type="submit">Открыть</button>
        </form>
      </div>
    </div>
  );
}
