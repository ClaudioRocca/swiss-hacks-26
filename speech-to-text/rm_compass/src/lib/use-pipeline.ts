/**
 * WebSocket hook that connects to the FastAPI pipeline backend.
 *
 * Exposes reactive state:
 *  - transcriptLines: finalized utterances
 *  - partial: the current in-progress partial text
 *  - concepts: array of concept objects with executed query results
 *  - status: "idle" | "connecting" | "running" | "done" | "error"
 *
 * Usage:
 *   const { start, status, transcriptLines, partial, concepts } = usePipeline();
 *   <button onClick={() => start()}>Start Demo</button>
 */

import { useCallback, useRef, useState } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";

// --- Types matching the backend protocol ---

export type TranscriptLine = {
  text: string;
  timestamp: string; // HH:MM:SS derived from index
};

export type ExecutedQuery = {
  source: string;
  filters?: Record<string, unknown>;
  call?: { function: string; kwargs: Record<string, unknown> };
  error: string | null;
  result_count?: number;
  results: unknown;
};

export type Concept = {
  index: number;
  topic: string;
  summary: string;
  intent: string;
  entities: string[];
  text: string;
  data_requests: { source: string; rationale: string }[];
  executed_queries: ExecutedQuery[];
};

export type PipelineStatus = "idle" | "connecting" | "running" | "done" | "error";

export function usePipeline() {
  const [status, setStatus] = useState<PipelineStatus>("idle");
  const [transcriptLines, setTranscriptLines] = useState<TranscriptLine[]>([]);
  const [partial, setPartial] = useState("");
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const lineCountRef = useRef(0);

  const formatTime = (index: number): string => {
    const totalSeconds = index * 8; // rough ~8s per utterance for display
    const mm = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
    const ss = String(totalSeconds % 60).padStart(2, "0");
    return `00:${mm}:${ss}`;
  };

  const start = useCallback(
    (opts?: { file?: string; mode?: "text" | "audio" }) => {
      // Reset state
      setTranscriptLines([]);
      setPartial("");
      setConcepts([]);
      setErrorMessage(null);
      lineCountRef.current = 0;
      setStatus("connecting");

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("running");
        const msg: Record<string, string> = { type: "start" };
        if (opts?.file) msg.file = opts.file;
        if (opts?.mode) msg.mode = opts.mode;
        ws.send(JSON.stringify(msg));
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case "partial":
            setPartial(data.text);
            break;

          case "final":
            setPartial("");
            setTranscriptLines((prev) => [
              ...prev,
              { text: data.text, timestamp: formatTime(lineCountRef.current) },
            ]);
            lineCountRef.current += 1;
            break;

          case "concept":
            setConcepts((prev) => [...prev, data as Concept]);
            break;

          case "done":
            setStatus("done");
            ws.close();
            break;

          case "error":
            setStatus("error");
            setErrorMessage(data.message);
            ws.close();
            break;
        }
      };

      ws.onerror = () => {
        setStatus("error");
        setErrorMessage("WebSocket connection failed");
      };

      ws.onclose = () => {
        if (status !== "done" && status !== "error") {
          // Connection closed unexpectedly while still running
        }
      };
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const stop = useCallback(() => {
    wsRef.current?.close();
    setStatus("done");
  }, []);

  return {
    start,
    stop,
    status,
    transcriptLines,
    partial,
    concepts,
    errorMessage,
  };
}
