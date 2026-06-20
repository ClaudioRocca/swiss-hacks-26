import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  PhoneOff, Play, X, TrendingUp, Building2, ShieldCheck, Sparkles,
  CheckCircle2, Briefcase, Newspaper, BarChart3, Home, ChevronDown, ChevronUp,
} from "lucide-react";
import { useCallState } from "../lib/call-state";
import { useCallSession, fetchCustomerProfile, type CustomerProfile } from "../lib/call-session";
import { usePipeline, type Concept, type ExecutedQuery } from "../lib/use-pipeline";
import { TradingViewChart } from "../components/trading-view-chart";
import { extractTickersFromConcepts } from "../lib/ticker-utils";
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "../components/ui/resizable";

// Distinct accent colors tying each concept widget to its transcript lines.
const CONCEPT_COLORS = [
  "#B8955A", "#2E7D6B", "#9C4DCC", "#C2410C",
  "#1D4ED8", "#BE185D", "#0E7490", "#4D7C0F",
];
const colorForConcept = (index: number) => CONCEPT_COLORS[index % CONCEPT_COLORS.length];

export const Route = createFileRoute("/")({
  head: () => ({ meta: [{ title: "Live Call — RM Intelligence" }] }),
  component: LiveCallPage,
});

const GOLD = "#B8955A";
const GOLD_TEXT = "#92681F";
const NAVY = "#141E55";
const TEXT = "#1A1A2E";

// Keywords to highlight in transcript
const HIGHLIGHTS = [
  "estate planning", "real estate", "allocation", "portfolio",
  "gold", "Dubai", "ETF", "CHF", "exposure", "short", "Nestlé",
  "semiconductor", "geopolitical", "volatile", "safer assets",
  "commercial property", "Zurich", "Geneva",
];

function highlight(text: string) {
  const cleaned = text.replace(/\*\*/g, "");
  let parts: Array<{ s: string; hl: boolean }> = [{ s: cleaned, hl: false }];
  HIGHLIGHTS.forEach((term) => {
    const next: typeof parts = [];
    for (const p of parts) {
      if (p.hl) { next.push(p); continue; }
      let rest = p.s;
      let lower = rest.toLowerCase();
      let idx = lower.indexOf(term.toLowerCase());
      while (idx !== -1) {
        next.push({ s: rest.slice(0, idx), hl: false });
        next.push({ s: rest.slice(idx, idx + term.length), hl: true });
        rest = rest.slice(idx + term.length);
        lower = rest.toLowerCase();
        idx = lower.indexOf(term.toLowerCase());
      }
      next.push({ s: rest, hl: false });
    }
    parts = next.filter((p) => p.s.length > 0);
  });
  return parts.map((p, i) =>
    p.hl ? (
      <mark
        key={i}
        style={{
          background: "linear-gradient(120deg, rgba(184,149,90,0.12) 0%, rgba(184,149,90,0.18) 100%)",
          borderBottom: `1.5px solid ${GOLD}`,
          borderRadius: 3,
          padding: "1px 4px",
          color: GOLD_TEXT,
          fontWeight: 500,
        }}
      >
        {p.s}
      </mark>
    ) : (
      <span key={i}>{p.s}</span>
    ),
  );
}

// ---------------------------------------------------------------------------
// Icon mapping for concept sources
// ---------------------------------------------------------------------------

function iconForSource(source: string) {
  switch (source) {
    case "portfolio": return Briefcase;
    case "trades": return BarChart3;
    case "market_movements": return TrendingUp;
    case "real_estate": return Home;
    case "news": return Newspaper;
    case "customer_profile": return ShieldCheck;
    default: return Building2;
  }
}

// ---------------------------------------------------------------------------
// Widget body renderers per data source
// ---------------------------------------------------------------------------

function PortfolioResults({ results }: { results: unknown }) {
  const rows = results as Array<Record<string, unknown>>;
  if (!rows?.length) return <EmptyResults />;
  return (
    <div className="space-y-2">
      {rows.map((r, i) => (
        <div key={i} className="flex items-baseline justify-between border-b pb-2 last:border-0 last:pb-0" style={{ borderColor: "#F1ECE0" }}>
          <div>
            <span className="font-semibold" style={{ color: NAVY }}>{String(r.ticker)}</span>
            <span className="ml-2 text-xs" style={{ color: "#6B7280" }}>{String(r.sector)}</span>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium" style={{ color: TEXT }}>
              {Number(r.quantity).toLocaleString()} @ {String(r.currency)} {Number(r.current_price).toFixed(1)}
            </div>
            <div className="text-xs" style={{ color: Number(r.profit_loss) >= 0 ? "#16A34A" : "#DC2626" }}>
              P&L: {Number(r.profit_loss) >= 0 ? "+" : ""}{Number(r.profit_loss).toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function MarketMovementsResults({ results }: { results: unknown }) {
  const rows = results as Array<Record<string, unknown>>;
  if (!rows?.length) return <EmptyResults />;
  // Show top 5 most significant moves
  const top = [...rows].sort((a, b) => Math.abs(Number(b.percentage_change)) - Math.abs(Number(a.percentage_change))).slice(0, 5);
  return (
    <div className="space-y-2">
      {top.map((r, i) => (
        <div key={i} className="flex items-center justify-between">
          <div>
            <span className="text-sm font-medium" style={{ color: NAVY }}>{String(r.ticker)}</span>
            <span className="ml-2 text-xs" style={{ color: "#6B7280" }}>{String(r.company_name)}</span>
          </div>
          <div
            className="rounded-full px-2.5 py-0.5 text-xs font-semibold tabular"
            style={{
              background: Number(r.percentage_change) >= 0 ? "#F0FDF4" : "#FEF2F2",
              color: Number(r.percentage_change) >= 0 ? "#15803D" : "#DC2626",
              border: `1px solid ${Number(r.percentage_change) >= 0 ? "#BBF7D0" : "#FECACA"}`,
            }}
          >
            {Number(r.percentage_change) >= 0 ? "+" : ""}{Number(r.percentage_change).toFixed(2)}%
          </div>
        </div>
      ))}
    </div>
  );
}

function RealEstateResults({ results }: { results: unknown }) {
  const rows = results as Array<Record<string, unknown>>;
  if (!rows?.length) return <EmptyResults label="No matching properties" />;
  return (
    <div className="space-y-2">
      {rows.map((r, i) => (
        <div key={i} className="rounded-xl px-3 py-2 text-xs" style={{ background: "#FAFAF7", border: "1px solid #F1ECE0" }}>
          <div className="font-medium" style={{ color: TEXT }}>{String(r.location)} — {String(r.property_type)}</div>
          <div style={{ color: "#6B7280" }}>
            Value: CHF {Number(r.current_value).toLocaleString()} · Status: {String(r.status)}
          </div>
        </div>
      ))}
    </div>
  );
}

function NewsResults({ results }: { results: unknown }) {
  const rows = results as Array<Record<string, unknown>>;
  if (!rows?.length) return <EmptyResults label="No relevant news" />;
  return (
    <div className="space-y-2">
      {rows.slice(0, 3).map((r, i) => (
        <NewsItem key={i} row={r} />
      ))}
    </div>
  );
}

function NewsItem({ row }: { row: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);
  const meta = row.metadata as Record<string, string> | undefined;
  const doc = String(row.document);
  const isLong = doc.length > 120;
  return (
    <div className="rounded-xl px-3 py-2 text-xs" style={{ background: "#FAFAF7", border: "1px solid #F1ECE0" }}>
      <div className="font-medium leading-snug" style={{ color: TEXT }}>
        {expanded || !isLong ? doc : `${doc.slice(0, 120)}…`}
      </div>
      <div className="mt-1 flex items-center justify-between gap-2" style={{ color: "#6B7280" }}>
        <span>{meta?.source} · {meta?.category}</span>
        {isLong && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="press inline-flex items-center gap-1 font-semibold uppercase tracking-wider"
            style={{ color: NAVY, fontSize: 10 }}
          >
            {expanded ? <>Collapse <ChevronUp className="h-3 w-3" /></> : <>Read full <ChevronDown className="h-3 w-3" /></>}
          </button>
        )}
      </div>
    </div>
  );
}

function TradesResults({ results }: { results: unknown }) {
  const rows = results as Array<Record<string, unknown>>;
  if (!rows?.length) return <EmptyResults />;
  return (
    <div className="space-y-2">
      {rows.slice(0, 5).map((r, i) => (
        <div key={i} className="flex items-baseline justify-between border-b pb-2 last:border-0 last:pb-0" style={{ borderColor: "#F1ECE0" }}>
          <div>
            <span className="font-semibold" style={{ color: NAVY }}>{String(r.ticker)}</span>
            <span className="ml-2 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase" style={{ background: "#F3F4F6", color: "#6B7280" }}>
              {String(r.operation_type)}
            </span>
          </div>
          <span className="text-sm" style={{ color: TEXT }}>CHF {Number(r.value).toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

function CustomerProfileResults({ results }: { results: unknown }) {
  const data = results as Record<string, unknown> | null;
  if (!data || Object.keys(data).length === 0) return <EmptyResults />;
  // Map real data-layer fields -> display label + optional formatter.
  const fields: Array<[string, string, ((v: unknown) => string)?]> = [
    ["name", "Client"],
    ["risk_appetite", "Risk appetite"],
    ["investment_horizon", "Horizon", (v) => String(v).replace(/_/g, " ")],
    ["total_aum", "Total AUM", (v) => `CHF ${Number(v).toLocaleString()}`],
    ["preferred_sectors", "Preferred sectors", (v) => String(v).replace(/,/g, ", ")],
    ["kyc_status", "KYC"],
  ];
  return (
    <div className="space-y-2 text-sm">
      {fields.filter(([k]) => data[k] != null).map(([k, label, fmt]) => (
        <div key={k} className="flex items-baseline justify-between border-b pb-2 last:border-0 last:pb-0" style={{ borderColor: "#F1ECE0" }}>
          <span className="text-[11px] uppercase tracking-wider" style={{ color: "#6B7280" }}>{label}</span>
          <span className="font-medium" style={{ color: TEXT }}>{fmt ? fmt(data[k]) : String(data[k])}</span>
        </div>
      ))}
    </div>
  );
}

function EmptyResults({ label = "No results" }: { label?: string }) {
  return <div className="text-xs italic" style={{ color: "#9CA3AF" }}>{label}</div>;
}

function QueryResultBody({ query }: { query: ExecutedQuery }) {
  if (query.error) {
    return <div className="text-xs" style={{ color: "#DC2626" }}>Error: {query.error}</div>;
  }
  switch (query.source) {
    case "portfolio": return <PortfolioResults results={query.results} />;
    case "market_movements": return <MarketMovementsResults results={query.results} />;
    case "real_estate": return <RealEstateResults results={query.results} />;
    case "news": return <NewsResults results={query.results} />;
    case "trades": return <TradesResults results={query.results} />;
    case "customer_profile": return <CustomerProfileResults results={query.results} />;
    default: return <pre className="text-xs overflow-auto max-h-32">{JSON.stringify(query.results, null, 2)}</pre>;
  }
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

function LiveCallPage() {
  const navigate = useNavigate();
  const { callEnded, endCall, elapsed } = useCallState();
  const { saveSession, clearSession } = useCallSession();
  const { start, stop, status, transcriptLines, partial, concepts } = usePipeline();
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [customerProfile, setCustomerProfile] = useState<CustomerProfile | null>(null);

  const isLive = status === "running";
  const isDone = status === "done";
  const isIdle = status === "idle";

  // Fetch customer profile once on mount (needed for post-call analysis)
  useEffect(() => {
    fetchCustomerProfile()
      .then(setCustomerProfile)
      .catch((err) => console.warn("Could not fetch customer profile:", err));
  }, []);

  // Auto-save session when pipeline finishes (handles both manual end and natural completion)
  const sessionSavedRef = useRef(false);
  useEffect(() => {
    if (isDone && transcriptLines.length > 0 && !sessionSavedRef.current) {
      sessionSavedRef.current = true;
      saveSession({
        transcriptLines,
        concepts,
        customerProfile,
        callDurationSeconds: elapsed,
        clientName: "Mr. Alessandro Ferretti",
      });
    }
    if (isIdle) {
      sessionSavedRef.current = false;
    }
  }, [isDone, isIdle, transcriptLines, concepts, customerProfile, elapsed, saveSession]);

  // Extract tickers from concepts and auto-select the latest one
  const detectedTickers = useMemo(() => extractTickersFromConcepts(concepts), [concepts]);
  const hasCharts = detectedTickers.length > 0;

  // Auto-select latest ticker when new ones appear
  useEffect(() => {
    if (detectedTickers.length > 0) {
      setSelectedTicker(detectedTickers[detectedTickers.length - 1]);
    }
  }, [detectedTickers.length]);

  // --- Visual link between widgets and the transcript lines that triggered them ---
  // Map each transcript line index -> the concept it belongs to.
  const lineToConcept = useMemo(() => {
    const m = new Map<number, number>();
    concepts.forEach((c) => (c.line_indices ?? []).forEach((li) => m.set(li, c.index)));
    return m;
  }, [concepts]);

  // The concept currently "flashed" (highlighted in both panels). Set on a new
  // trigger and on widget click; cleared after a few seconds.
  const [flashConcept, setFlashConcept] = useState<number | null>(null);
  const flashTimer = useRef<number | null>(null);
  const lineRefs = useRef<Map<number, HTMLDivElement | null>>(new Map());
  // True while a user-clicked flash holds, so auto-scroll yields to the click.
  const clickHoldRef = useRef(false);

  const flash = (conceptIndex: number, fromClick = false) => {
    setFlashConcept(conceptIndex);
    clickHoldRef.current = fromClick;
    if (flashTimer.current) window.clearTimeout(flashTimer.current);
    flashTimer.current = window.setTimeout(() => {
      setFlashConcept(null);
      clickHoldRef.current = false;
    }, 3500);
  };

  // Auto-flash the newest concept when it arrives.
  const prevConceptCount = useRef(0);
  useEffect(() => {
    if (concepts.length > prevConceptCount.current) {
      flash(concepts[concepts.length - 1].index);
    }
    prevConceptCount.current = concepts.length;
  }, [concepts]);

  // Click a widget -> scroll its first generating line into view and flash both.
  const handleWidgetClick = (concept: Concept) => {
    flash(concept.index, true);
    const first = (concept.line_indices ?? [])[0];
    if (first != null) {
      lineRefs.current.get(first)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  // Auto-scroll transcript to bottom — but yield while a clicked widget is
  // holding its generating lines in view.
  useEffect(() => {
    if (clickHoldRef.current) return;
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcriptLines, partial]);

  const handleStart = () => {
    clearSession(); // clear any previous session
    start(); // uses default text file
  };

  const handleEndCall = () => {
    stop();
    endCall();
  };

  return (
    <div className="relative flex h-screen flex-col bg-white">
      {/* Progress bar */}
      {isLive && (
        <div className="absolute inset-x-0 top-0 z-20 h-[2px] overflow-hidden">
          <div className="h-full w-full progress-flow" />
        </div>
      )}

      {/* Header */}
      <header
        className="shrink-0 flex items-center justify-between px-8 py-4 text-white"
        style={{
          background: "rgba(10, 18, 64, 0.98)",
          borderBottom: "1px solid rgba(184,149,90,0.2)",
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05)",
        }}
      >
        <div className="flex items-center gap-6">
          <div>
            <div className="font-serif text-white" style={{ fontSize: 22 }}>Mr. Alessandro Ferretti</div>
          </div>
          {isDone || callEnded ? (
            <div
              className="inline-flex items-center gap-2 px-3 py-1"
              style={{ border: "1px solid rgba(255,255,255,0.2)", background: "rgba(255,255,255,0.05)", borderRadius: 20 }}
            >
              <CheckCircle2 className="h-3 w-3 text-white/70" />
              <span className="text-[11px] font-semibold uppercase tracking-wider text-white/70">Call Ended</span>
            </div>
          ) : null}
        </div>
        <div className="flex items-center gap-3">
          {isIdle && (
            <button
              onClick={handleStart}
              className="press inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white transition-colors"
              style={{ background: GOLD, borderRadius: 10 }}
            >
              <Play className="h-4 w-4" />
              Start Demo
            </button>
          )}
          {isLive && (
            <button
              onClick={handleEndCall}
              className="press inline-flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors"
              style={{ background: "transparent", border: "1px solid rgba(239,68,68,0.6)", color: "#ef4444", borderRadius: 10 }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(239,68,68,0.1)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <PhoneOff className="h-4 w-4" />
              End Call
            </button>
          )}
          {isDone && (
            <button
              onClick={() => navigate({ to: "/post-call" })}
              className="press inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white transition-colors"
              style={{ background: GOLD, borderRadius: 10 }}
            >
              View Report →
            </button>
          )}
        </div>
      </header>

      {/* Main content: transcript left, widgets right (+ chart when tickers detected) — horizontally resizable */}
      <ResizablePanelGroup orientation="horizontal" className="flex-1 min-h-0">
        <ResizablePanel defaultSize={60} minSize={35}>
        {/* Transcript panel */}
        <section className="flex h-full min-h-0 flex-col" style={{ background: "#FAFAF9", borderRight: "1px solid #E5E7EB" }}>
          <div className="flex items-center justify-between border-b px-8 py-3" style={{ borderColor: "rgba(20,30,85,0.08)", background: "#FAFAF9" }}>
            <div className="text-[11px] font-medium uppercase tracking-[0.18em]" style={{ color: "#6B7280" }}>Live Transcript</div>
          </div>
          <div
            className="relative flex-1 overflow-y-auto px-8 py-6"
            style={{ background: "#FAFAF9", boxShadow: "inset 0 4px 12px rgba(10,18,64,0.04)" }}
          >
            {isIdle && transcriptLines.length === 0 && (
              <div className="flex h-full min-h-[300px] items-center justify-center">
                <div className="text-center">
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full" style={{ background: "#F3F4F6" }}>
                    <Play className="h-5 w-5" style={{ color: "#6B7280" }} />
                  </div>
                  <div className="font-serif text-lg" style={{ color: TEXT }}>Ready to Begin</div>
                  <div className="mt-1 text-sm" style={{ color: "#6B7280" }}>Click "Start Demo" to begin live transcription</div>
                </div>
              </div>
            )}

            {transcriptLines.map((line, i) => {
              const isRM = line.speaker === "rm";
              const conceptIdx = lineToConcept.get(i);
              const cColor = conceptIdx != null ? colorForConcept(conceptIdx) : null;
              const isFlashed = conceptIdx != null && conceptIdx === flashConcept;
              return (
                <div
                  key={i}
                  ref={(el) => { lineRefs.current.set(i, el); }}
                  className="flex animate-fade-up py-1.5"
                  style={{
                    animationDelay: `${Math.min(i, 5) * 30}ms`,
                    justifyContent: isRM ? "flex-end" : "flex-start",
                  }}
                >
                  <div
                    className="max-w-[78%] transition-all duration-300"
                    style={{ transform: isFlashed ? "scale(1.025)" : "scale(1)" }}
                  >
                    <div
                      className="flex items-baseline gap-2 mb-0.5"
                      style={{ flexDirection: isRM ? "row-reverse" : "row" }}
                    >
                      <span
                        className="text-[10px] font-semibold uppercase tracking-wider"
                        style={{ color: isRM ? GOLD : "#6B7280" }}
                      >
                        {isRM ? "Relationship Manager" : "Client"}
                      </span>
                      <span className="text-[10px] tabular" style={{ color: "#9CA3AF" }}>
                        {line.timestamp}
                      </span>
                    </div>
                    <div
                      style={{
                        background: isFlashed
                          ? (cColor ? `${cColor}22` : undefined)
                          : (isRM ? NAVY : "#FFFFFF"),
                        color: isFlashed ? "#1C1C2E" : (isRM ? "#FFFFFF" : "#1C1C2E"),
                        border: isFlashed && cColor
                          ? `1px solid ${cColor}`
                          : (isRM ? "none" : "1px solid #E5E7EB"),
                        borderRadius: 16,
                        borderTopRightRadius: isRM ? 4 : 16,
                        borderTopLeftRadius: isRM ? 16 : 4,
                        // persistent thin accent tying the line to its widget's color
                        borderRightWidth: !isRM && cColor ? 0 : undefined,
                        borderLeft: !isRM && cColor ? `3px solid ${cColor}` : undefined,
                        borderRight: isRM && cColor ? `3px solid ${cColor}` : undefined,
                        padding: "8px 12px",
                        fontSize: 14,
                        lineHeight: 1.6,
                        boxShadow: isFlashed && cColor
                          ? `0 0 0 3px ${cColor}33, 0 2px 8px rgba(10,18,64,0.12)`
                          : "0 1px 2px rgba(10,18,64,0.06)",
                        transition: "all 300ms",
                      }}
                    >
                      {highlight(line.text)}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Partial (in-progress) line — client side */}
            {partial && (
              <div className="flex justify-start py-1.5 opacity-60">
                <div className="max-w-[78%]">
                  <div className="text-[10px] font-semibold uppercase tracking-wider mb-0.5" style={{ color: "#6B7280" }}>
                    Client
                  </div>
                  <div
                    style={{
                      background: "#FFFFFF",
                      color: "#1C1C2E",
                      border: "1px solid #E5E7EB",
                      borderRadius: 16,
                      borderTopLeftRadius: 4,
                      padding: "8px 12px",
                      fontSize: 14,
                      lineHeight: 1.6,
                      fontStyle: "italic",
                    }}
                  >
                    {partial}
                  </div>
                </div>
              </div>
            )}

            {/* Listening indicator */}
            {isLive && (
              <div className="flex items-center gap-2 pl-20 pt-3 text-xs" style={{ color: GOLD }}>
                <span className="inline-flex gap-1">
                  <span className="bounce-dot h-1.5 w-1.5 rounded-full" style={{ background: GOLD, animationDelay: "0ms" }} />
                  <span className="bounce-dot h-1.5 w-1.5 rounded-full" style={{ background: GOLD, animationDelay: "150ms" }} />
                  <span className="bounce-dot h-1.5 w-1.5 rounded-full" style={{ background: GOLD, animationDelay: "300ms" }} />
                </span>
                Listening…
              </div>
            )}

            {isDone && transcriptLines.length > 0 && (
              <div className="flex items-center gap-2 pt-6 text-xs" style={{ color: "#6B7280" }}>
                <CheckCircle2 className="h-3.5 w-3.5" />
                Call ended — {concepts.length} strong intent signal detected
              </div>
            )}

            <div ref={transcriptEndRef} />
          </div>
        </section>
        </ResizablePanel>

        <ResizableHandle withHandle />

        <ResizablePanel defaultSize={40} minSize={25}>
        {/* Widgets panel — dynamic from concepts */}
        <aside className="flex h-full min-h-0 flex-col" style={{ background: NAVY }}>
          <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.02] px-6 py-3">
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-white/50">Contextual Intelligence</div>
            <div
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider"
              style={{
                background: "rgba(184,149,90,0.08)",
                color: GOLD,
                border: "1px solid rgba(184,149,90,0.25)",
                borderRadius: 20,
              }}
            >
              <Sparkles className="h-3 w-3" /> {concepts.length} detected
            </div>
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
            {concepts.map((concept, i) => (
              <ConceptWidget
                key={concept.index}
                concept={concept}
                animDelay={i * 80}
                color={colorForConcept(concept.index)}
                isFlashed={flashConcept === concept.index}
                onClick={() => handleWidgetClick(concept)}
              />
            ))}
            {concepts.length === 0 && (
              <div className="glass rounded-2xl p-8 text-center">
                <div className="text-sm font-medium text-white/80">
                  {isIdle ? "Waiting for call" : "Listening for intents…"}
                </div>
                <div className="mt-1 text-xs text-white/50">
                  Widgets appear when the AI detects actionable topics
                </div>
              </div>
            )}
          </div>
        </aside>

        </ResizablePanel>

        {/* TradingView Chart Panel — appears when tickers are detected */}
        {hasCharts && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={30} minSize={20}>
              <section className="flex h-full min-h-0 flex-col" style={{ background: "#0F1629", borderLeft: "1px solid rgba(184,149,90,0.15)" }}>
                {/* Ticker tabs */}
                <div className="flex items-center gap-1 overflow-x-auto border-b border-white/10 px-4 py-2">
                  <TrendingUp className="h-3.5 w-3.5 shrink-0" style={{ color: GOLD }} />
                  <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wider mr-2" style={{ color: GOLD }}>
                    Charts
                  </span>
                  {detectedTickers.map((ticker) => (
                    <button
                      key={ticker}
                      onClick={() => setSelectedTicker(ticker)}
                      className="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors"
                      style={{
                        background: selectedTicker === ticker ? "rgba(184,149,90,0.15)" : "transparent",
                        color: selectedTicker === ticker ? GOLD : "rgba(255,255,255,0.6)",
                        border: selectedTicker === ticker ? `1px solid ${GOLD}` : "1px solid transparent",
                      }}
                    >
                      {ticker.includes(":") ? ticker.split(":")[1] : ticker}
                    </button>
                  ))}
                </div>
                {/* Chart */}
                <div className="flex-1 min-h-0">
                  {selectedTicker && (
                    <TradingViewChart symbol={selectedTicker} theme="dark" />
                  )}
                </div>
              </section>
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Concept widget card
// ---------------------------------------------------------------------------

function ConceptWidget({
  concept,
  animDelay,
  color,
  isFlashed,
  onClick,
}: {
  concept: Concept;
  animDelay: number;
  color: string;
  isFlashed: boolean;
  onClick: () => void;
}) {
  // Pick icon from the primary data source
  const primarySource = concept.executed_queries[0]?.source || concept.data_requests[0]?.source || "portfolio";
  const Icon = iconForSource(primarySource);

  return (
    <article
      onClick={onClick}
      title="Click to highlight the messages that generated this"
      style={{
        animationDelay: `${animDelay}ms`,
        background: "#FFFFFF",
        // colored top accent ties the widget to its transcript lines
        borderTop: `3px solid ${color}`,
        border: `1px solid ${isFlashed ? color : "rgba(184,149,90,0.18)"}`,
        borderTopWidth: 3,
        borderTopColor: color,
        borderRadius: 18,
        boxShadow: isFlashed
          ? `0 0 0 3px ${color}33, 0 8px 28px rgba(10,18,64,0.16)`
          : "0 4px 24px rgba(10,18,64,0.07), 0 1px 4px rgba(10,18,64,0.04)",
        transform: isFlashed ? "scale(1.015)" : "scale(1)",
        transition: "all 300ms",
        cursor: "pointer",
      }}
      className="animate-slide-in-right p-5"
    >
      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className="flex h-9 w-9 items-center justify-center text-white"
            style={{ background: `linear-gradient(135deg, ${color}, ${color}cc)`, borderRadius: 12 }}
          >
            <Icon className="h-4 w-4" strokeWidth={1.7} />
          </div>
          <div>
            <div className="font-serif leading-tight" style={{ color: NAVY, fontSize: 15, fontWeight: 600 }}>{concept.topic}</div>
            <div className="uppercase" style={{ color: GOLD, fontSize: 9, letterSpacing: "0.15em", fontWeight: 600 }}>
              {concept.entities.slice(0, 3).join(" · ") || primarySource}
            </div>
          </div>
        </div>
      </div>

      {/* Summary */}
      <p className="mb-4 text-xs leading-relaxed" style={{ color: "#6B7280" }}>{concept.summary}</p>

      {/* Query results */}
      <div className="space-y-3">
        {concept.executed_queries.map((q, qi) => (
          <div key={qi}>
            {concept.executed_queries.length > 1 && (
              <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider" style={{ color: GOLD }}>
                {q.source.replace(/_/g, " ")} {q.result_count != null ? `(${q.result_count})` : ""}
              </div>
            )}
            <QueryResultBody query={q} />
          </div>
        ))}
        {concept.executed_queries.length === 0 && (
          <div className="text-xs italic" style={{ color: "#9CA3AF" }}>No data queries for this concept</div>
        )}
      </div>
    </article>
  );
}
