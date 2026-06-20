import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  AlertTriangle, CheckCircle2, ArrowLeft,
  Download, Loader2, Newspaper,
} from "lucide-react";
import { toast } from "sonner";
import {
  useCallSession,
  fetchPostCallAnalysis,
  type PostCallAnalysis,
} from "../lib/call-session";
import type { Concept } from "../lib/use-pipeline";

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
        {analysis && <AnalysisContent analysis={analysis} concepts={sessionData.concepts} />}
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

function AnalysisContent({ analysis, concepts }: { analysis: PostCallAnalysis; concepts: Concept[] }) {
  // Extract news articles from executed queries (source === "news")
  const newsArticles = extractNewsFromConcepts(concepts);

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

      {/* Risk Profile — expanded, right below summary */}
      <Card className="col-span-12">
        <CardHeader title="Risk Profile Comparison" eyebrow="Risk Shift Detection" />
        <RiskToleranceSection risk={analysis.risk_tolerance} />
      </Card>
      {/* Conversation sentiment analysis — actionable sentiment with context */}
      <Card className="col-span-12">
        <CardHeader title="Conversation sentiment analysis" eyebrow="Engagement Signals" />
        <SentimentSection sentiment={analysis.sentiment} />
      </Card>

      {/* Emotional Signals — compact layout */}
      <Card className="col-span-12">
        <CardHeader title="Emotional Signals" eyebrow="Client Emotions" />
        <EmotionalTopics topics={analysis.emotional_topics} />
      </Card>

      {/* Relevant Market News — from call data */}
      {newsArticles.length > 0 && (
        <Card className="col-span-12">
          <CardHeader title="Relevant Market Context" eyebrow="News Retrieved During Call" />
          <NewsSection articles={newsArticles} />
        </Card>
      )}

      {/* Action Items */}
      <Card className="col-span-12">
        <CardHeader title="Action Items" eyebrow="Follow-up" />
        <ul className="space-y-3">
          {analysis.action_items.map((item, i) => (
            <ActionItem key={i} priority={item.priority} text={item.text} due={item.due_suggestion} />
          ))}
        </ul>
      </Card>
    </>
  );
}

// ---------------------------------------------------------------------------
// Sentiment Section
// ---------------------------------------------------------------------------

function SentimentSection({ sentiment }: { sentiment: PostCallAnalysis["sentiment"] }) {
  const points = sentiment.bands;
  if (!points.length) return null;

  // Chart dimensions
  const W = 600, H = 140, PAD_X = 56, PAD_Y = 16;
  const chartW = W - PAD_X - 20; // right padding smaller
  const chartH = H - PAD_Y * 2;
  const midY = PAD_Y + chartH * 0.5; // 50-score line

  // Map data points to SVG coords
  const coords = points.map((p) => ({
    x: PAD_X + (p.at_percent / 100) * chartW,
    y: PAD_Y + chartH - (p.score / 100) * chartH,
    score: p.score,
  }));

  // Build smooth curve (catmull-rom to bezier)
  const linePath = smoothPath(coords.map((c) => [c.x, c.y]));
  // Area: same curve, closed to bottom
  const areaPath = `${linePath} L ${coords[coords.length - 1].x} ${PAD_Y + chartH} L ${coords[0].x} ${PAD_Y + chartH} Z`;

  // Peak positions on the curve (interpolate Y from nearest data)
  const peakCoords = sentiment.peaks.map((p) => {
    const px = PAD_X + (p.at_percent / 100) * chartW;
    // Linear interpolation between closest data points
    let py = midY;
    for (let i = 0; i < coords.length - 1; i++) {
      if (px >= coords[i].x && px <= coords[i + 1].x) {
        const t = (px - coords[i].x) / (coords[i + 1].x - coords[i].x);
        py = coords[i].y + t * (coords[i + 1].y - coords[i].y);
        break;
      }
    }
    return { x: px, y: py, ...p };
  });

  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-[11px]" style={{ color: MUTED }}>
        <span>Call start</span>
        <span>Call end</span>
      </div>

      {/* SVG Area Chart */}
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 160 }}>
        <defs>
          <linearGradient id="sentiment-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={GOLD} stopOpacity="0.35" />
            <stop offset="100%" stopColor={GOLD} stopOpacity="0.03" />
          </linearGradient>
        </defs>

        {/* Horizontal grid lines */}
        {[0, 25, 50, 75, 100].map((v) => {
          const y = PAD_Y + chartH - (v / 100) * chartH;
          return (
            <line
              key={v}
              x1={PAD_X} y1={y} x2={PAD_X + chartW} y2={y}
              stroke={v === 50 ? "#D1D5DB" : "#F3F4F6"}
              strokeWidth={v === 50 ? "1" : "0.5"}
              strokeDasharray={v === 50 ? "4 3" : "none"}
            />
          );
        })}

        {/* Area fill */}
        <path d={areaPath} fill="url(#sentiment-fill)" />

        {/* Curve line */}
        <path d={linePath} fill="none" stroke={NAVY} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

        {/* Data points */}
        {coords.map((c, i) => (
          <circle key={i} cx={c.x} cy={c.y} r="3" fill={NAVY} stroke="#fff" strokeWidth="1.5" />
        ))}

        {/* Peak markers — color derived from position on curve, not tone */}
        {peakCoords.map((p, i) => {
          // Score at this peak's position (interpolated)
          const score = 100 - ((p.y - PAD_Y) / chartH) * 100;
          const dotColor = score >= 50 ? GOLD : "#DC2626";
          return (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r="5.5" fill={dotColor} stroke="#fff" strokeWidth="2" />
            </g>
          );
        })}

        {/* Y-axis labels — descriptive */}
        <text x={PAD_X - 6} y={PAD_Y + 4} textAnchor="end" fontSize="9" fill={MUTED}>Receptive</text>
        <text x={PAD_X - 6} y={midY + 3} textAnchor="end" fontSize="9" fill={MUTED}>Neutral</text>
        <text x={PAD_X - 6} y={PAD_Y + chartH + 4} textAnchor="end" fontSize="9" fill={MUTED}>Guarded</text>
      </svg>

      {/* Legend */}
      <div className="mt-1 flex items-center gap-4 text-[10px]" style={{ color: MUTED }}>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full" style={{ background: GOLD }} /> Receptive moment
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full" style={{ background: "#DC2626" }} /> Guarded moment
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-[1px] w-4 inline-block border-t border-dashed" style={{ borderColor: "#D1D5DB" }} /> Neutral (50)
        </span>
      </div>

      {/* Peak annotations */}
      <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
        {sentiment.peaks.map((p, i) => {
          // Determine color from interpolated score at this peak position
          const peakData = peakCoords[i];
          const score = peakData ? 100 - ((peakData.y - PAD_Y) / chartH) * 100 : 50;
          const dotColor = score >= 50 ? GOLD : "#DC2626";
          return (
            <div
              key={i}
              className="flex items-start gap-2 px-3 py-2"
              style={{
                background: "#FAFAF9",
                border: `1px solid ${dotColor}33`,
                borderRadius: 10,
              }}
            >
              <span
                className="mt-1 h-2 w-2 shrink-0 rounded-full"
                style={{ background: dotColor }}
              />
              <span className="text-xs leading-relaxed" style={{ color: TEXT }}>{p.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Generate a smooth SVG path from points using Catmull-Rom → cubic bezier conversion. */
function smoothPath(pts: number[][]): string {
  if (pts.length < 2) return "";
  if (pts.length === 2) return `M ${pts[0][0]} ${pts[0][1]} L ${pts[1][0]} ${pts[1][1]}`;

  let d = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(i - 1, 0)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(i + 2, pts.length - 1)];

    // Catmull-Rom to cubic bezier control points (tension = 0.5)
    const cp1x = p1[0] + (p2[0] - p0[0]) / 6;
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6;
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6;
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6;

    d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2[0]} ${p2[1]}`;
  }
  return d;
}

// ---------------------------------------------------------------------------
// Emotional Topics
// ---------------------------------------------------------------------------

function EmotionalTopics({ topics }: { topics: PostCallAnalysis["emotional_topics"] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {topics.map((t, i) => {
        const cfg = EMOTION_CONFIG[t.emotion];
        return (
          <div
            key={i}
            className="p-3"
            style={{ background: "#FAFAF9", border: `1px solid ${BORDER}`, borderRadius: 12 }}
          >
            <div className="flex items-center gap-2 mb-1.5">
              <span
                className="rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider"
                style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}
              >
                {cfg.label}
              </span>
              <span className="text-xs font-medium truncate" style={{ color: NAVY }}>{t.topic}</span>
            </div>
            <blockquote
              className="mb-1.5 pl-2.5 text-xs italic leading-relaxed"
              style={{ borderLeft: `2px solid ${cfg.color}`, color: BODY }}
            >
              "{t.quote}"
            </blockquote>
            <p className="text-[11px] leading-snug" style={{ color: MUTED }}>{t.explanation}</p>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Risk Tolerance Comparison
// ---------------------------------------------------------------------------

function RiskToleranceSection({ risk }: { risk: PostCallAnalysis["risk_tolerance"] }) {
  return (
    <div className="space-y-5">
      {/* Gauge charts — side by side */}
      <div className="grid grid-cols-2 gap-6">
        <RiskGauge label="KYC Profile" level={risk.known_profile} />
        <RiskGauge label="Detected in Call" level={risk.detected_appetite} />
      </div>

      {/* Shift indicator */}
      {risk.shift_detected ? (
        <div
          className="flex items-center gap-3 p-4 rounded-xl"
          style={{ background: "#FEF9F0", border: `1px solid ${GOLD}44` }}
        >
          <AlertTriangle className="h-5 w-5 shrink-0" style={{ color: GOLD }} />
          <div>
            <span className="text-sm font-medium" style={{ color: NAVY }}>
              Profile shift detected: {RISK_DISPLAY[risk.known_profile]} → {RISK_DISPLAY[risk.detected_appetite]}
            </span>
            <p className="text-xs mt-0.5" style={{ color: MUTED }}>
              The client's expressed preferences diverge from their recorded profile.
            </p>
          </div>
        </div>
      ) : (
        <div
          className="flex items-center gap-3 p-4 rounded-xl"
          style={{ background: "#F8FFFE", border: "1px solid #D1FAE5" }}
        >
          <CheckCircle2 className="h-5 w-5 shrink-0" style={{ color: "#059669" }} />
          <span className="text-sm font-medium" style={{ color: NAVY }}>
            Detected appetite aligns with known profile
          </span>
        </div>
      )}

      {/* Evidence */}
      <div>
        <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: GOLD }}>Evidence from conversation</div>
        <ul className="space-y-2">
          {risk.evidence.map((e, i) => (
            <li key={i} className="flex items-start gap-2 text-xs" style={{ color: BODY }}>
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: GOLD }} />
              {e}
            </li>
          ))}
        </ul>
      </div>

      {/* Comparison notes */}
      <p className="text-xs leading-relaxed" style={{ color: MUTED }}>
        {risk.comparison_notes}
      </p>
    </div>
  );
}

/**
 * Semi-circle gauge chart for risk level visualization.
 *
 * Uses a neutral gradient (teal → gold → navy) — risk appetite isn't
 * inherently good or bad. The needle comparison between the two gauges
 * is what communicates the shift.
 */
function RiskGauge({ label, level }: { label: string; level: "conservative" | "moderate" | "aggressive" }) {
  // The arc sweeps from left (180°) to right (0°) — a half circle above center.
  // Needle angles: conservative → left (180°), moderate → top (90°), aggressive → right (0°).
  // In our SVG coordinate system (0° = right, counter-clockwise):
  //   conservative = 180° from positive-x = left
  //   moderate = 90° from positive-x = top
  //   aggressive = 0° from positive-x = right
  const angleMap = { conservative: 180, moderate: 90, aggressive: 0 };
  const needleAngleDeg = angleMap[level];

  const cx = 100, cy = 100, r = 72;
  const needleLen = 55;
  const gradId = `gauge-grad-${label.replace(/\s+/g, "-").toLowerCase()}`;

  // Needle endpoint (SVG: 0° is right, angles go counter-clockwise for upper half)
  const rad = (needleAngleDeg * Math.PI) / 180;
  const nx = cx + needleLen * Math.cos(rad);
  const ny = cy - needleLen * Math.sin(rad); // subtract because SVG y is inverted

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 115" className="w-full max-w-[200px]">
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0D9488" />
            <stop offset="50%" stopColor="#B8955A" />
            <stop offset="100%" stopColor="#1E3A5F" />
          </linearGradient>
        </defs>
        {/* Background track (light) */}
        <path
          d={describeArc(cx, cy, r, 180, 0)}
          fill="none"
          stroke="#F1ECE0"
          strokeWidth="16"
          strokeLinecap="round"
        />
        {/* Colored gradient arc */}
        <path
          d={describeArc(cx, cy, r, 180, 0)}
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth="16"
          strokeLinecap="round"
        />
        {/* Tick marks at the three positions */}
        {[180, 90, 0].map((angle) => {
          const a = (angle * Math.PI) / 180;
          const rInner = r - 12;
          const rOuter = r - 4;
          return (
            <line
              key={angle}
              x1={cx + rInner * Math.cos(a)}
              y1={cy - rInner * Math.sin(a)}
              x2={cx + rOuter * Math.cos(a)}
              y2={cy - rOuter * Math.sin(a)}
              stroke="#9CA3AF"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          );
        })}
        {/* Needle */}
        <line
          x1={cx}
          y1={cy}
          x2={nx}
          y2={ny}
          stroke={NAVY}
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        {/* Center hub */}
        <circle cx={cx} cy={cy} r="6" fill={NAVY} />
        <circle cx={cx} cy={cy} r="3" fill="#fff" />
      </svg>
      {/* Axis labels */}
      <div className="w-full max-w-[200px] flex justify-between px-1 -mt-1">
        <span className="text-[9px]" style={{ color: MUTED }}>Conservative</span>
        <span className="text-[9px]" style={{ color: MUTED }}>Aggressive</span>
      </div>
      {/* Title + value */}
      <div className="mt-2 text-center">
        <div className="text-[10px] uppercase tracking-wider" style={{ color: MUTED }}>{label}</div>
        <div className="text-sm font-semibold" style={{ color: NAVY }}>{RISK_DISPLAY[level]}</div>
      </div>
    </div>
  );
}

/** Describe an SVG arc path for the upper half-circle (angles in degrees, 0°=right, CCW positive). */
function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number): string {
  // Convert to SVG cartesian (y-inverted)
  const startRad = (startAngle * Math.PI) / 180;
  const endRad = (endAngle * Math.PI) / 180;
  const x1 = cx + r * Math.cos(startRad);
  const y1 = cy - r * Math.sin(startRad);
  const x2 = cx + r * Math.cos(endRad);
  const y2 = cy - r * Math.sin(endRad);
  // For a half circle (180° sweep), large-arc-flag = 0, sweep-flag = 1 (clockwise in SVG)
  return `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`;
}

// ---------------------------------------------------------------------------
// News extraction from call data + rendering
// ---------------------------------------------------------------------------

type NewsArticle = {
  document: string;
  source: string;
  category: string;
  published_date: string;
  tickers_mentioned: string;
};

function extractNewsFromConcepts(concepts: Concept[]): NewsArticle[] {
  const seen = new Set<string>();
  const articles: NewsArticle[] = [];

  for (const concept of concepts) {
    for (const eq of concept.executed_queries) {
      if (eq.source !== "news" || eq.error) continue;
      const results = eq.results as Array<Record<string, unknown>> | null;
      if (!Array.isArray(results)) continue;
      for (const r of results) {
        const doc = String(r.document || "");
        if (!doc || seen.has(doc)) continue;
        seen.add(doc);
        const meta = (r.metadata || {}) as Record<string, string>;
        articles.push({
          document: doc,
          source: meta.source || "",
          category: meta.category || "",
          published_date: meta.published_date || "",
          tickers_mentioned: meta.tickers_mentioned || "",
        });
      }
    }
  }
  return articles;
}

function NewsSection({ articles }: { articles: NewsArticle[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      {articles.map((a, i) => (
        <article
          key={i}
          className="flex flex-col gap-2 p-4"
          style={{ background: "#FAFAF9", border: `1px solid ${BORDER}`, borderRadius: 14 }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Newspaper className="h-3.5 w-3.5" style={{ color: GOLD }} />
              <span
                className="rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider"
                style={{ background: GOLD + "1A", color: "#8a6f29", border: `1px solid ${GOLD}55` }}
              >
                {a.category || "Market"}
              </span>
            </div>
            {a.published_date && (
              <span className="text-[10px]" style={{ color: MUTED }}>{a.published_date}</span>
            )}
          </div>
          <p className="text-xs leading-relaxed flex-1" style={{ color: TEXT }}>
            {a.document.length > 180 ? `${a.document.slice(0, 180)}…` : a.document}
          </p>
          <div className="flex items-center justify-between pt-1 border-t" style={{ borderColor: BORDER }}>
            <span className="text-[10px] font-medium" style={{ color: MUTED }}>{a.source}</span>
            {a.tickers_mentioned && (
              <span className="text-[10px]" style={{ color: NAVY }}>
                {a.tickers_mentioned}
              </span>
            )}
          </div>
        </article>
      ))}
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
