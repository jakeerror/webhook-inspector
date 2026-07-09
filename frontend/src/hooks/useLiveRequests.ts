import { useEffect, useState } from "react";

import { wsUrl } from "../api/client";
import { binsApi } from "../api/endpoints";
import type { CapturedRequestSummary, LiveEvent } from "../api/types";

/**
 * Live-tail: seed from history, then prepend requests streamed over WebSocket.
 * Auto-reconnects on drop (SPEC §4).
 */
export function useLiveRequests(binId: string) {
  const [requests, setRequests] = useState<CapturedRequestSummary[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let closed = false;
    let socket: WebSocket | null = null;

    binsApi
      .requests(binId)
      .then(setRequests)
      .catch(() => undefined);

    const connect = () => {
      socket = new WebSocket(wsUrl(binId));
      socket.onopen = () => setConnected(true);
      socket.onclose = () => {
        setConnected(false);
        if (!closed) setTimeout(connect, 2000);
      };
      socket.onmessage = (event) => {
        const msg = JSON.parse(event.data) as LiveEvent;
        if (msg.type === "request") {
          setRequests((prev) => [msg.data, ...prev]);
        }
      };
    };
    connect();

    return () => {
      closed = true;
      socket?.close();
    };
  }, [binId]);

  return { requests, connected };
}
