import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import {
  PhoneOff, Play, X, TrendingUp, Building2, ShieldCheck, Sparkles,
  CheckCircle2, Briefcase, Newspaper, BarChart3, Home, ChevronDown, ChevronUp,
} from "lucide-react";
import { useCallState } from "../lib/call-state";
import { usePipeline, type Concept, type ExecutedQuery } from "../lib/use-pipeline";

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
  const display = ["full_name", "risk_profile", "aum_chf", "residency", "relationship_since"];
  return (
    <div className="space-y-2 text-sm">
      {display.filter((k) => data[k] != null).map((k) => (
        <div key={k} className="flex items-baseline justify-between border-b pb-2 last:border-0 last:pb-0" style={{ borderColor: "#F1ECE0" }}>
          <span className="text-[11px] uppercase tracking-wider" style={{ color: "#6B7280" }}>{k.replace(/_/g, " ")}</span>
          <span className="font-medium" style={{ color: TEXT }}>{String(data[k])}</span>
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
  const { callEnded, endCall } = useCallState();
  const { start, stop, status, transcriptLines, partial, concepts } = usePipeline();
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  const isLive = status === "running";
  const isDone = status === "done";
  const isIdle = status === "idle";

  // Auto-scroll transcript to bottom
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcriptLines, partial]);

  const handleStart = () => {
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
        className="flex items-center justify-between px-8 py-4 text-white"
        style={{
          background: "rgba(10, 18, 64, 0.98)",
          borderBottom: "1px solid rgba(184,149,90,0.2)",
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05)",
        }}
      >
        <div className="flex items-center gap-6">
          <div>
            <div style={{ color: "rgba(184,149,90,0.8)", letterSpacing: "0.2em", fontSize: 10, textTransform: "uppercase", fontWeight: 600 }}>
              {isIdle ? "Ready" : "Active Call"}
            </div>
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
          ) : isLive ? (
            <div
              className="inline-flex items-center gap-2"
              style={{
                background: "transparent",
                border: "1px solid #ef4444",
                color: "#ef4444",
                borderRadius: 20,
                padding: "4px 12px",
                fontSize: 11,
                letterSpacing: "0.1em",
                fontWeight: 600,
              }}
            >
              <span className="h-1.5 w-1.5 animate-blink rounded-full" style={{ background: "#ef4444" }} />
              LIVE
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

      {/* Main content: transcript left, widgets right */}
      <div className="grid flex-1 min-h-0 grid-cols-[60%_40%]">
        {/* Transcript panel */}
        <section className="flex min-h-0 flex-col" style={{ background: "#FAFAF9", borderRight: "1px solid #E5E7EB" }}>
          <div className="flex items-center justify-between border-b px-8 py-3" style={{ borderColor: "rgba(20,30,85,0.08)", background: "#FAFAF9" }}>
            <div className="text-[11px] font-medium uppercase tracking-[0.18em]" style={{ color: "#6B7280" }}>Live Transcript</div>
            <div className="text-[11px]" style={{ color: "#6B7280" }}>
              {transcriptLines.length} utterance{transcriptLines.length !== 1 ? "s" : ""}
            </div>
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
              return (
                <div
                  key={i}
                  className="flex animate-fade-up py-1.5"
                  style={{
                    animationDelay: `${Math.min(i, 5) * 30}ms`,
                    justifyContent: isRM ? "flex-end" : "flex-start",
                  }}
                >
                  <div className="max-w-[78%]">
                    <div
                      className="text-[10px] font-semibold uppercase tracking-wider mb-0.5"
                      style={{ color: isRM ? GOLD : "#6B7280", textAlign: isRM ? "right" : "left" }}
                    >
                      {isRM ? "Relationship Manager" : "Client"}
                    </div>
                    <div
                      style={{
                        background: isRM ? NAVY : "#FFFFFF",
                        color: isRM ? "#FFFFFF" : "#1C1C2E",
                        border: isRM ? "none" : "1px solid #E5E7EB",
                        borderRadius: 16,
                        borderTopRightRadius: isRM ? 4 : 16,
                        borderTopLeftRadius: isRM ? 16 : 4,
                        padding: "8px 12px",
                        fontSize: 14,
                        lineHeight: 1.6,
                        boxShadow: "0 1px 2px rgba(10,18,64,0.06)",
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
                Pipeline complete — {transcriptLines.length} utterances, {concepts.length} concepts detected
              </div>
            )}

            <div ref={transcriptEndRef} />
          </div>
        </section>

        {/* Widgets panel — dynamic from concepts */}
        <aside className="flex min-h-0 flex-col" style={{ background: NAVY }}>
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
              <ConceptWidget key={concept.index} concept={concept} animDelay={i * 80} />
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
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Concept widget card
// ---------------------------------------------------------------------------

function ConceptWidget({ concept, animDelay }: { concept: Concept; animDelay: number }) {
  // Pick icon from the primary data source
  const primarySource = concept.executed_queries[0]?.source || concept.data_requests[0]?.source || "portfolio";
  const Icon = iconForSource(primarySource);

  return (
    <article
      style={{
        animationDelay: `${animDelay}ms`,
        background: "#FFFFFF",
        border: "1px solid rgba(184,149,90,0.18)",
        borderRadius: 18,
        boxShadow: "0 4px 24px rgba(10,18,64,0.07), 0 1px 4px rgba(10,18,64,0.04)",
      }}
      className="animate-slide-in-right p-5"
    >
      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className="flex h-9 w-9 items-center justify-center text-white"
            style={{ background: "linear-gradient(135deg, #141E55, #1e2d7a)", borderRadius: 12 }}
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
