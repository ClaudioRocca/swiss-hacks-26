import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type CallState = {
  elapsed: number;
  callEnded: boolean;
  dismissedWidgets: Set<string>;
  endCall: () => void;
  dismissWidget: (id: string) => void;
};

const Ctx = createContext<CallState | null>(null);

const START_SECONDS = 4 * 60 + 23;

export function CallStateProvider({ children }: { children: ReactNode }) {
  const [elapsed, setElapsed] = useState(START_SECONDS);
  const [callEnded, setCallEnded] = useState(false);
  const [dismissedWidgets, setDismissedWidgets] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (callEnded) return;
    const id = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [callEnded]);

  const value = useMemo<CallState>(
    () => ({
      elapsed,
      callEnded,
      dismissedWidgets,
      endCall: () => setCallEnded(true),
      dismissWidget: (id) => setDismissedWidgets((d) => new Set(d).add(id)),
    }),
    [elapsed, callEnded, dismissedWidgets]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCallState() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useCallState must be used within CallStateProvider");
  return v;
}

export function formatDuration(s: number) {
  const hh = String(Math.floor(s / 3600)).padStart(2, "0");
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}
