import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  AlertTriangle, CheckCircle2, ArrowLeft,
  Download, Loader2,
  ShieldAlert, ShieldCheck, Shield, X,
} from "lucide-react";
import { toast } from "sonner";
import {
  useCallSession,
  fetchPostCallAnalysis,
  type PostCallAnalysis,
} from "../lib/call-session";

export const Route = createFileRoute("/post-call")({
  head: () => ({ meta: [{ title: "Post-Call Dashboard — RM Intelligence" }] }),
  component: PostCallPage,
});

// Design tokens (preserved from original)
const TEXT = "#1A1A2E";
const BODY = "#374151";
const MUTED = "#6B7280";
const BORDER = "rgba(20,30,85,0.08)";
const CARD_BG = "#FFFFFF";
const SOFT = "#F3F4F6";
const PAGE_BG = "#F8F7F4";
const NAVY = "#141E55";
const GOLD = "#B8955A";

const TONE_COLOR = {
  positive: "#16A34A",
  neutral: "#D97706",
  concerned: "#DC2626",
} as const;

const EMOTION_CONFIG = {
  fear: { color: "#DC2626", bg: "#FEF2F2", border: "#FECACA", label: "Fear" },
  joy: { color: "#16A34A", bg: "#F0FDF4", border: "#BBF7D0", label: "Joy" },
  concern: { color: "#D97706", bg: "#FFFBEB", border: "#FDE68A", label: "Concern" },
  confidence: { color: "#1D4ED8", bg: "#DBEAFE", border: "#93C5FD", label: "Confidence" },
  frustration: { color: "#9333EA", bg: "#FAF5FF", border: "#D8B4FE", label: "Frustration" },
} as const;

const PRIORITY_CONFIG = {
  HIGH: { pill: { bg: "#FEF2F2", text: "#DC2626", border: "#FECACA" }, bar: "#DC2626" },
  MED: { pill: { bg: "#FFFBEB", text: "#D97706", border: "#FDE68A" }, bar: "#D97706" },
  LOW: { pill: { bg: "#F0FDF4", text: "#16A34A", border: "#BBF7D0" }, bar: "#16A34A" },
} as const;

const RISK_LEVELS = ["conservative", "moderate", "aggressive"] as const;
const RISK_DISPLAY = { conservative: "Conservative", moderate: "Moderate", aggressive: "Aggressive" };
const RISK_COLORS = { conservative: "#16A34A", moderate: "#D97706", aggressive: "#DC2626" };

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

function PostCallPage() {
  const navigate = useNavigate();
  const { sessionData } = useCallSession();
  const [analysis, setAnalysis] = useState<PostCallAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionData) return;
    setLoading(true);
    setError(null);
    fetchPostCallAnalysis(sessionData)
      .then(setAnalysis)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [sessionData]);

  // No session data — user navigated here directly
  if (!sessionData) {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: PAGE_BG }}>
        <div className="text-center">
          <div className="font-serif text-xl" style={{ color: TEXT }}>No call data available</div>
          <p className="mt-2 text-sm" style={{ color: MUTED }}>
            Complete a live call first, then click "View Report" to generate the analysis.
          </p>
          <button
            onClick={() => navigate({ to: "/" })}
            className="mt-4 inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white"
            style={{ background: NAVY }}
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Live Call
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ color: TEXT, background: PAGE_BG }}>
      <Header clientName={sessionData.clientName} loading={loading} />
      <div className="px-10 py-8 grid grid-cols-12 gap-6 max-w-[1440px]">
        {loading && <LoadingState />}
        {error && <ErrorState message={error} onRetry={() => {
          setLoading(true); setError(null);
          fetchPostCallAnalysis(sessionData)
            .then(setAnalysis)
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false));
        }} />}
        {analysis && <AnalysisContent analysis={analysis} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

function Header({ clientName, loading }: { clientName: string; loading: boolean }) {
  const today = new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  return (
    <header className="sticky top-0 z-30 flex items-start justify-between border-b px-10 py-7" style={{ borderColor: BORDER, background: PAGE_BG }}>
      <div>
        <div className="text-[11px] uppercase tracking-[0.18em]" style={{ color: GOLD }}>Post-Call Analysis</div>
        <h1 className="mt-1 font-serif text-3xl" style={{ color: TEXT }}>
          {clientName} <span style={{ color: MUTED }}>— {today}</span>
        </h1>
        <p className="mt-1 text-sm" style={{ color: MUTED }}>
          {loading ? "Generating AI analysis…" : "AI-generated insights from call"}
        </p>
      </div>
      <button
        onClick={() => toast("Export queued", { description: "Preparing PDF report…" })}
        className="press inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium hover:bg-[#F9FAFB]"
        style={{ borderColor: BORDER, color: TEXT, background: CARD_BG }}
      >
        <Download className="h-3.5 w-3.5" />
        Export PDF
      </button>
    </header>
  );
}

// ---------------------------------------------------------------------------
// Loading & Error states
// ---------------------------------------------------------------------------

function LoadingState() {
  return (
    <div className="col-span-12 flex flex-col items-center justify-center py-20">
      <Loader2 className="h-8 w-8 animate-spin" style={{ color: GOLD }} />
      <div className="mt-4 font-serif text-lg" style={{ color: TEXT }}>Analyzing call data…</div>
      <p className="mt-1 text-sm" style={{ color: MUTED }}>
        The AI is reviewing the transcript, sentiment, and risk indicators.
      </p>
      <div className="mt-6 grid grid-cols-3 gap-8 text-center text-xs" style={{ color: MUTED }}>
        <div><div className="mb-1 h-2 w-2 mx-auto rounded-full animate-pulse" style={{ background: GOLD }} />Transcript</div>
        <div><div className="mb-1 h-2 w-2 mx-auto rounded-full animate-pulse" style={{ background: GOLD, animationDelay: "0.3s" }} />Sentiment</div>
        <div><div className="mb-1 h-2 w-2 mx-auto rounded-full animate-pulse" style={{ background: GOLD, animationDelay: "0.6s" }} />Risk Profile</div>
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="col-span-12 flex flex-col items-center justify-center py-16">
      <AlertTriangle className="h-8 w-8" style={{ color: "#DC2626" }} />
      <div className="mt-3 font-serif text-lg" style={{ color: TEXT }}>Analysis failed</div>
      <p className="mt-1 text-sm" style={{ color: MUTED }}>{message}</p>
      <button
        onClick={onRetry}
        className="mt-4 rounded-xl px-4 py-2 text-sm font-medium text-white"
        style={{ background: NAVY }}
      >
        Retry Analysis
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Analysis Content — renders the AI response
// ---------------------------------------------------------------------------

function AnalysisContent({ analysis }: { analysis: PostCallAnalysis }) {
  const [riskModalOpen, setRiskModalOpen] = useState(false);

  return (
    <>
      {/* Summary */}
      <Card className="col-span-12">
        <CardHeader title="Call Summary" eyebrow="Overview" />
        <p className="text-[15px] leading-relaxed" style={{ color: TEXT }}>
          {analysis.summary}
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          {analysis.tags.map((t) => (
            <span
              key={t}
              className="rounded-full border px-3 py-1 text-xs font-medium"
              style={{ borderColor: GOLD + "66", background: GOLD + "1A", color: "#8a6f29" }}
            >
              #{t.replace(/^#/, "")}
            </span>
          ))}
        </div>
      </Card>

      {/* Sentiment bar (compact — no peak list, no overall ring) */}
      <Card className="col-span-12">
        <CardHeader title="Conversation Sentiment" eyebrow="Sentiment" />
        <SentimentSection sentiment={analysis.sentiment} />
      </Card>

      {/* Emotional Signals — elevated position */}
      <Card className="col-span-12">
        <CardHeader title="Emotional Signals" eyebrow="Client Emotions" />
        <EmotionalTopics topics={analysis.emotional_topics} />
      </Card>

      {/* Risk Profile — shown as a prominent trigger card that opens a modal */}
      <Card className="col-span-12">
        <RiskTriggerCard risk={analysis.risk_tolerance} onOpen={() => setRiskModalOpen(true)} />
      </Card>

      {/* Action Items */}
      <Card className="col-span-12">
        <CardHeader title="Action Items" eyebrow="Follow-up" />
        <ul className="space-y-3">
          {analysis.action_items.map((item, i) => (
            <ActionItem key={i} priority={item.priority} text={item.text} due={item.due_suggestion} />
          ))}
        </ul>
      </Card>

      {/* Risk Profile Modal */}
      {riskModalOpen && (
        <RiskModal risk={analysis.risk_tolerance} onClose={() => setRiskModalOpen(false)} />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Sentiment Section
// ---------------------------------------------------------------------------

function SentimentSection({ sentiment }: { sentiment: PostCallAnalysis["sentiment"] }) {
  // Build gradient from bands
  const gradientStops = sentiment.bands.map((b) => {
    const color = TONE_COLOR[b.tone];
    return `${color} ${b.from_percent}%, ${color} ${b.to_percent}%`;
  }).join(", ");

  return (
    <div>
      <div className="mb-3 flex items-center justify-between text-[11px]" style={{ color: MUTED }}>
        <span>Start</span>
        <span>Sentiment across call duration</span>
        <span>End</span>
      </div>
      {/* Bar with hover-only peak tooltips */}
      <div className="relative w-full" style={{ paddingTop: 18, paddingBottom: 4 }}>
        {/* Peak dot markers — positioned above the bar */}
        {sentiment.peaks.map((p, i) => (
          <div
            key={i}
            className="group absolute -translate-x-1/2"
            style={{ left: `${p.at_percent}%`, top: 4, zIndex: 20 }}
          >
            <span
              className="block h-3 w-3 rounded-full ring-2 ring-white cursor-pointer"
              style={{ background: TONE_COLOR[p.tone], boxShadow: "0 1px 4px rgba(10,18,64,0.2)" }}
            />
            {/* Tooltip — shown ABOVE the dot on hover */}
            <div
              className="pointer-events-none absolute left-1/2 bottom-full mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-lg px-3 py-1.5 text-[11px] text-white shadow-xl group-hover:block"
              style={{ background: NAVY, zIndex: 50 }}
            >
              {p.label}
              <div className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent" style={{ borderTopColor: NAVY }} />
            </div>
          </div>
        ))}
        {/* Gradient bar */}
        <div
          className="relative h-[8px] w-full overflow-hidden rounded-full"
          style={{ background: `linear-gradient(90deg, ${gradientStops})` }}
        />
      </div>
      <div className="mt-3 flex gap-4 text-[11px]" style={{ color: MUTED }}>
        <Legend color={TONE_COLOR.positive} label="Positive" />
        <Legend color={TONE_COLOR.neutral} label="Neutral" />
        <Legend color={TONE_COLOR.concerned} label="Concerned" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Emotional Topics
// ---------------------------------------------------------------------------

function EmotionalTopics({ topics }: { topics: PostCallAnalysis["emotional_topics"] }) {
  return (
    <div className="space-y-3">
      {topics.map((t, i) => {
        const cfg = EMOTION_CONFIG[t.emotion];
        return (
          <div
            key={i}
            className="p-4"
            style={{ background: "#FAFAF9", border: `1px solid ${BORDER}`, borderRadius: 14 }}
          >
            <div className="flex items-center gap-2 mb-2">
              <span
                className="rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider"
                style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}
              >
                {cfg.label}
              </span>
              <span className="text-sm font-medium" style={{ color: NAVY }}>{t.topic}</span>
            </div>
            <blockquote
              className="mb-2 pl-3 text-sm italic"
              style={{ borderLeft: `3px solid ${cfg.color}`, color: BODY }}
            >
              "{t.quote}"
            </blockquote>
            <p className="text-xs" style={{ color: MUTED }}>{t.explanation}</p>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Risk Profile — Trigger card (teaser) + full Modal
// ---------------------------------------------------------------------------

function RiskTriggerCard({ risk, onOpen }: { risk: PostCallAnalysis["risk_tolerance"]; onOpen: () => void }) {
  const shifted = risk.shift_detected;
  return (
    <div
      className="flex items-center justify-between cursor-pointer transition-shadow hover:shadow-lg"
      onClick={onOpen}
      style={{ margin: -28, padding: 28 }}
    >
      <div className="flex items-center gap-4">
        <div
          className="flex h-12 w-12 items-center justify-center rounded-2xl"
          style={{
            background: shifted ? "#FEF2F2" : "#F0FDF4",
            border: `1px solid ${shifted ? "#FECACA" : "#BBF7D0"}`,
          }}
        >
          {shifted
            ? <AlertTriangle className="h-5 w-5" style={{ color: "#DC2626" }} />
            : <ShieldCheck className="h-5 w-5" style={{ color: "#16A34A" }} />
          }
        </div>
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em]" style={{ color: GOLD }}>
            Risk Shift Detection
          </div>
          <div className="font-serif text-lg" style={{ color: NAVY }}>
            {shifted
              ? `Shift detected: ${RISK_DISPLAY[risk.known_profile]} → ${RISK_DISPLAY[risk.detected_appetite]}`
              : "Profile aligned — no shift detected"
            }
          </div>
          <p className="text-xs mt-0.5" style={{ color: MUTED }}>Click to view full risk profile comparison</p>
        </div>
      </div>
      <div
        className="rounded-xl px-4 py-2 text-sm font-medium"
        style={{ background: NAVY, color: "#fff" }}
      >
        View Details
      </div>
    </div>
  );
}

function RiskModal({ risk, onClose }: { risk: PostCallAnalysis["risk_tolerance"]; onClose: () => void }) {
  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(10,18,64,0.6)", backdropFilter: "blur(4px)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="relative w-full max-w-xl mx-4 max-h-[85vh] overflow-y-auto rounded-3xl p-8"
        style={{ background: CARD_BG, boxShadow: "0 25px 60px rgba(10,18,64,0.25)" }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 flex h-8 w-8 items-center justify-center rounded-full hover:bg-gray-100"
          aria-label="Close"
        >
          <X className="h-4 w-4" style={{ color: MUTED }} />
        </button>

        <div className="text-[10px] font-semibold uppercase tracking-[0.2em]" style={{ color: GOLD }}>
          Risk Shift Detection
        </div>
        <h2 className="mt-1 font-serif text-2xl" style={{ color: NAVY }}>
          Risk Profile Comparison
        </h2>
        <p className="mt-1 text-sm" style={{ color: MUTED }}>
          Comparing known KYC profile with appetite detected in the conversation.
        </p>

        <div className="mt-6">
          <RiskToleranceSection risk={risk} />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Risk Tolerance Comparison (used inside the modal)
// ---------------------------------------------------------------------------

function RiskToleranceSection({ risk }: { risk: PostCallAnalysis["risk_tolerance"] }) {
  const KnownIcon = risk.known_profile === "conservative" ? ShieldCheck
    : risk.known_profile === "aggressive" ? ShieldAlert : Shield;
  const DetectedIcon = risk.detected_appetite === "conservative" ? ShieldCheck
    : risk.detected_appetite === "aggressive" ? ShieldAlert : Shield;

  return (
    <div className="space-y-4">
      {/* Visual comparison */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-4 text-center" style={{ background: "#FAFAF9", border: `1px solid ${BORDER}`, borderRadius: 14 }}>
          <KnownIcon className="mx-auto h-6 w-6 mb-2" style={{ color: RISK_COLORS[risk.known_profile] }} />
          <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: MUTED }}>KYC Profile</div>
          <div className="text-sm font-semibold" style={{ color: RISK_COLORS[risk.known_profile] }}>
            {RISK_DISPLAY[risk.known_profile]}
          </div>
        </div>
        <div className="p-4 text-center" style={{ background: "#FAFAF9", border: `1px solid ${BORDER}`, borderRadius: 14 }}>
          <DetectedIcon className="mx-auto h-6 w-6 mb-2" style={{ color: RISK_COLORS[risk.detected_appetite] }} />
          <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: MUTED }}>Detected in Call</div>
          <div className="text-sm font-semibold" style={{ color: RISK_COLORS[risk.detected_appetite] }}>
            {RISK_DISPLAY[risk.detected_appetite]}
          </div>
        </div>
      </div>

      {/* Shift indicator */}
      {risk.shift_detected ? (
        <div
          className="flex items-center gap-2 p-3 rounded-xl"
          style={{ background: "#FEF2F2", border: "1px solid #FECACA" }}
        >
          <AlertTriangle className="h-4 w-4 shrink-0" style={{ color: "#DC2626" }} />
          <span className="text-xs font-medium" style={{ color: "#DC2626" }}>
            Risk appetite shift detected — profile review may be warranted
          </span>
        </div>
      ) : (
        <div
          className="flex items-center gap-2 p-3 rounded-xl"
          style={{ background: "#F0FDF4", border: "1px solid #BBF7D0" }}
        >
          <CheckCircle2 className="h-4 w-4 shrink-0" style={{ color: "#16A34A" }} />
          <span className="text-xs font-medium" style={{ color: "#16A34A" }}>
            Detected appetite aligns with known profile
          </span>
        </div>
      )}

      {/* Scale visualization */}
      <div className="px-2">
        <div className="flex justify-between text-[10px] mb-1" style={{ color: MUTED }}>
          {RISK_LEVELS.map((l) => <span key={l}>{RISK_DISPLAY[l]}</span>)}
        </div>
        <div className="relative h-2 rounded-full overflow-hidden" style={{ background: SOFT }}>
          <div className="absolute inset-0 rounded-full"
            style={{ background: "linear-gradient(90deg, #16A34A, #D97706, #DC2626)" , opacity: 0.3 }} />
          {/* Known marker */}
          <div
            className="absolute top-1/2 -translate-y-1/2 h-3.5 w-3.5 rounded-full border-2 border-white"
            style={{
              left: `${RISK_LEVELS.indexOf(risk.known_profile) * 50}%`,
              background: RISK_COLORS[risk.known_profile],
              boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
            }}
            title="KYC Profile"
          />
          {/* Detected marker */}
          <div
            className="absolute top-1/2 -translate-y-1/2 h-3.5 w-3.5 rounded-sm border-2 border-white rotate-45"
            style={{
              left: `${RISK_LEVELS.indexOf(risk.detected_appetite) * 50}%`,
              background: RISK_COLORS[risk.detected_appetite],
              boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
            }}
            title="Detected in Call"
          />
        </div>
        <div className="flex gap-4 mt-2 text-[10px]" style={{ color: MUTED }}>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full" style={{ background: RISK_COLORS[risk.known_profile] }} />
            KYC
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-sm rotate-45" style={{ background: RISK_COLORS[risk.detected_appetite] }} />
            Detected
          </span>
        </div>
      </div>

      {/* Evidence */}
      <div>
        <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: GOLD }}>Evidence</div>
        <ul className="space-y-2">
          {risk.evidence.map((e, i) => (
            <li key={i} className="flex items-start gap-2 text-xs" style={{ color: BODY }}>
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: GOLD }} />
              {e}
            </li>
          ))}
        </ul>
      </div>

      {/* Notes */}
      <p className="text-xs leading-relaxed" style={{ color: MUTED }}>
        {risk.comparison_notes}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared UI primitives
// ---------------------------------------------------------------------------

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section
      className={"p-7 " + className}
      style={{
        background: CARD_BG,
        border: `1px solid ${BORDER}`,
        borderRadius: 20,
        boxShadow: "0 2px 16px rgba(10,18,64,0.05)",
      }}
    >
      {children}
    </section>
  );
}

function CardHeader({ title, eyebrow }: { title: string; eyebrow?: string }) {
  return (
    <div className="mb-5">
      {eyebrow && (
        <div style={{ color: GOLD, fontSize: 10, letterSpacing: "0.2em", fontWeight: 600, textTransform: "uppercase" }}>
          {eyebrow}
        </div>
      )}
      <h2 className="font-serif" style={{ color: NAVY, fontSize: 22 }}>{title}</h2>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="h-2 w-2 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

function ActionItem({ priority, text, due }: { priority: "HIGH" | "MED" | "LOW"; text: string; due: string }) {
  const [done, setDone] = useState(false);
  const p = PRIORITY_CONFIG[priority];
  return (
    <li
      className="group relative flex items-start gap-3 overflow-hidden"
      style={{
        background: "#FFFFFF",
        border: "1px solid rgba(20,30,85,0.06)",
        borderRadius: 12,
        padding: "14px 16px",
        paddingLeft: 20,
      }}
    >
      <span className="absolute left-0 top-0 h-full" style={{ background: p.bar, width: 3 }} />
      <button
        onClick={() => setDone((d) => !d)}
        aria-label="Toggle complete"
        className="mt-0.5 flex h-[18px] w-[18px] items-center justify-center rounded-full"
        style={{
          background: done ? NAVY : "transparent",
          border: done ? `1.5px solid ${NAVY}` : "1.5px solid #D1D5DB",
          color: "#fff",
        }}
      >
        {done && <CheckCircle2 className="h-3 w-3" strokeWidth={3} />}
      </button>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span
            style={{
              background: p.pill.bg,
              color: p.pill.text,
              border: `1px solid ${p.pill.border}`,
              borderRadius: 6,
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: "0.1em",
              padding: "2px 6px",
            }}
          >
            {priority}
          </span>
          <span className="text-sm" style={{ color: TEXT, textDecoration: done ? "line-through" : "none", opacity: done ? 0.5 : 1 }}>
            {text}
          </span>
        </div>
        <div className="mt-1.5 text-xs" style={{ color: "#9CA3AF" }}>
          {due}
        </div>
      </div>
    </li>
  );
}
