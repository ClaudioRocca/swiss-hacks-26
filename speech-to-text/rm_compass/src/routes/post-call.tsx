import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  AlertTriangle, Info, CheckCircle2, Calendar, Sparkles,
  TrendingUp, Building2, Landmark, Download, Send, MessageSquare, Newspaper, ExternalLink,
} from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/post-call")({
  head: () => ({ meta: [{ title: "Post-Call Dashboard — RM Intelligence" }] }),
  component: PostCallPage,
});

const TEXT = "#1A1A2E";
const BODY = "#374151";
const MUTED = "#6B7280";
const BORDER = "rgba(20,30,85,0.08)";
const CARD_BG = "#FFFFFF";
const SOFT = "#F3F4F6";
const PAGE_BG = "#F8F7F4";
const NAVY = "#141E55";
const GOLD = "#B8955A";

function PostCallPage() {
  return (
    <div className="min-h-screen" style={{ color: TEXT, background: PAGE_BG }}>
      <header className="flex items-start justify-between border-b px-10 py-7" style={{ borderColor: BORDER, background: PAGE_BG }}>
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em]" style={{ color: GOLD }}>Post-Call Analysis</div>
          <h1 className="mt-1 font-serif text-3xl" style={{ color: TEXT }}>
            Mr. Alessandro Ferretti <span style={{ color: MUTED }}>— June 20, 2026</span>
          </h1>
          <p className="mt-1 text-sm" style={{ color: MUTED }}>
            AI-generated insights from 47-minute call · Generated 12 minutes ago
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

      <div className="px-10 py-8 grid grid-cols-12 gap-6 max-w-[1440px]">
        <Card className="col-span-12">
          <CardHeader title="Call Summary" eyebrow="Overview" />
          <p className="text-[15px] leading-relaxed" style={{ color: TEXT }}>
            Mr. Ferretti expressed renewed interest in increasing his precious-metals allocation, targeting a 5–8% gold position
            across physical and ETF instruments. He also requested exposure to UAE residential real estate, with specific focus
            on Dubai Marina and Palm Jumeirah, and asked to revisit his estate planning structure before year-end given the
            maturity of his two children.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {["#Gold", "#RealEstate", "#EstatePlanning", "#PortfolioReview"].map((t) => (
              <span
                key={t}
                className="rounded-full border px-3 py-1 text-xs font-medium"
                style={{ borderColor: GOLD + "66", background: GOLD + "1A", color: "#8a6f29" }}
              >
                {t}
              </span>
            ))}
          </div>
        </Card>

        <Card className="col-span-12">
          <CardHeader title="Conversation Sentiment Analysis" eyebrow="Sentiment" />
          <SentimentBlock />
        </Card>

        <Card className="col-span-12">
          <CardHeader title="Relevant Market News" eyebrow="Context · Last 24h" icon={Newspaper} />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <NewsCard
              tag="Gold"
              source="Financial Times"
              time="2h ago"
              title="Gold rallies past $2,480/oz as central banks accelerate reserve diversification"
              summary="Sustained EM buying and softer real yields underpin the move; analysts revise year-end targets higher."
            />
            <NewsCard
              tag="UAE Real Estate"
              source="Bloomberg"
              time="5h ago"
              title="Dubai prime residential prices climb 18% YoY, Palm Jumeirah leads the pack"
              summary="Inventory remains tight in branded developments; foreign HNW buyers drive Q2 transaction volume."
            />
            <NewsCard
              tag="Estate Planning"
              source="Reuters"
              time="Yesterday"
              title="Swiss inheritance reform proposals advance — implications for cross-border families"
              summary="Federal council signals 2027 review window; advisors urge clients to revisit structures before year-end."
            />
          </div>
        </Card>

        <Card className="col-span-12">
          <CardHeader title="Action Items" eyebrow="Follow-up" />
          <ul className="space-y-3">
            <ActionItem priority="HIGH" text="Prepare gold allocation proposal (5–8% portfolio)" assignee="SL" due="Jun 24" />
            <ActionItem priority="HIGH" text="Schedule Dubai property viewing — Q3 2026" assignee="ML" due="Jul 02" />
            <ActionItem priority="MED" text="Book estate planning consultation with legal team" assignee="SL" due="Jul 15" />
            <ActionItem priority="LOW" text="Send quarterly performance report" assignee="AK" due="Jul 30" />
          </ul>
        </Card>

        <Card className="col-span-12">
          <CardHeader title="Ask the Intelligence Assistant" eyebrow="AI Assistant" icon={Sparkles} />
          <p className="-mt-3 mb-4 text-sm" style={{ color: MUTED }}>
            Ask questions about this call, client history, or market context.
          </p>
          <AIChat />
        </Card>
      </div>
    </div>
  );
}

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

function CardHeader({
  title, eyebrow, icon: Icon, right,
}: {
  title: string; eyebrow?: string; icon?: typeof Sparkles; right?: React.ReactNode;
}) {
  return (
    <div className="mb-5 flex items-start justify-between gap-4">
      <div>
        {eyebrow && (
          <div style={{ color: GOLD, fontSize: 10, letterSpacing: "0.2em", fontWeight: 600, textTransform: "uppercase" }}>
            {eyebrow}
          </div>
        )}
        <h2 className="font-serif flex items-center gap-2" style={{ color: NAVY, fontSize: 22 }}>
          {title}
          {Icon && <Icon className="h-4 w-4" style={{ color: GOLD }} />}
        </h2>
      </div>
      {right}
    </div>
  );
}

function ConfidenceRing({ value }: { value: number }) {
  const r = 18, c = 2 * Math.PI * r, off = c * (1 - value / 100);
  return (
    <div className="relative h-12 w-12">
      <svg viewBox="0 0 44 44" className="h-full w-full -rotate-90">
        <circle cx="22" cy="22" r={r} fill="none" stroke={SOFT} strokeWidth="4" />
        <circle cx="22" cy="22" r={r} fill="none" stroke={GOLD} strokeWidth="4" strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-[11px] font-semibold tabular" style={{ color: TEXT }}>{value}%</div>
    </div>
  );
}

const PRIORITY = {
  HIGH: { pill: { bg: "#FEF2F2", text: "#DC2626", border: "#FECACA" }, bar: "#DC2626" },
  MED: { pill: { bg: "#FFFBEB", text: "#D97706", border: "#FDE68A" }, bar: "#D97706" },
  LOW: { pill: { bg: "#F0FDF4", text: "#16A34A", border: "#BBF7D0" }, bar: "#16A34A" },
} as const;

function ActionItem({
  priority, text, assignee, due,
}: { priority: keyof typeof PRIORITY; text: string; assignee: string; due: string }) {
  const [done, setDone] = useState(false);
  const p = PRIORITY[priority];
  return (
    <li
      className="press group relative flex items-start gap-3 overflow-hidden"
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
        className="press mt-0.5 flex h-[18px] w-[18px] items-center justify-center rounded-full"
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
        <div className="mt-1.5 flex items-center gap-3" style={{ color: "#9CA3AF", fontSize: 12 }}>
          <span className="inline-flex items-center gap-1.5">
            <span className="flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-semibold text-white" style={{ background: NAVY }}>
              {assignee}
            </span>
            Assigned
          </span>
          <span>Due {due}</span>
        </div>
      </div>
    </li>
  );
}

function OpportunityRow({
  icon: Icon, title, detail,
}: { icon: typeof TrendingUp; title: string; detail: string }) {
  return (
    <div
      className="press flex items-center justify-between p-3"
      style={{ background: "#FAFAF9", border: "1px solid rgba(20,30,85,0.06)", borderRadius: 12 }}
    >
      <div className="flex items-center gap-3">
        <div
          className="flex h-9 w-9 items-center justify-center"
          style={{ background: "linear-gradient(135deg, #141E55, #1e2d7a)", borderRadius: 12, color: "#fff" }}
        >
          <Icon className="h-4 w-4" strokeWidth={1.7} />
        </div>
        <div>
          <div className="text-sm font-medium" style={{ color: TEXT }}>{title}</div>
          <div className="text-xs" style={{ color: MUTED }}>{detail}</div>
        </div>
      </div>
      <button
        onClick={() => toast.success("Proposal draft created", { description: title })}
        className="press transition-colors"
        style={{
          background: "transparent",
          border: "1px solid rgba(20,30,85,0.25)",
          color: NAVY,
          borderRadius: 10,
          fontSize: 12,
          letterSpacing: "0.05em",
          fontWeight: 500,
          padding: "6px 14px",
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = NAVY; e.currentTarget.style.color = "#fff"; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = NAVY; }}
      >
        Create Proposal
      </button>
    </div>
  );
}

function RiskRow({ level, text }: { level: "med" | "info"; text: string }) {
  const Icon = level === "info" ? Info : AlertTriangle;
  const colors = level === "info"
    ? { bg: "#DBEAFE", text: "#1D4ED8", border: "#93C5FD" }
    : { bg: "#FEF3C7", text: "#92400E", border: "#FCD34D" };
  return (
    <li
      className="flex items-start gap-3 p-3"
      style={{ background: "#FAFAF9", border: `1px solid ${BORDER}`, borderRadius: 12 }}
    >
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border" style={{ background: colors.bg, color: colors.text, borderColor: colors.border }}>
        <Icon className="h-3.5 w-3.5" />
      </span>
      <span className="pt-1 text-sm" style={{ color: TEXT }}>{text}</span>
    </li>
  );
}

function RecRow({ text, score }: { text: string; score: number }) {
  return (
    <div className="p-3" style={{ background: "#FAFAF9", border: `1px solid ${BORDER}`, borderRadius: 12 }}>
      <div className="flex items-start gap-3">
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" style={{ color: GOLD }} />
        <p className="text-sm" style={{ color: TEXT }}>{text}</p>
      </div>
      <div className="mt-3 flex items-center gap-3 pl-7">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full" style={{ background: SOFT }}>
          <div className="h-full rounded-full" style={{ width: `${score}%`, background: GOLD }} />
        </div>
        <span className="text-[11px] tabular" style={{ color: MUTED }}>Confidence {score}%</span>
      </div>
    </div>
  );
}

const TIMELINE = [
  { date: "Jun 22", label: "Send macro brief on gold", tone: "navy" },
  { date: "Jun 24", label: "Gold allocation proposal", tone: "gold" },
  { date: "Jul 02", label: "Dubai property shortlist", tone: "navy" },
  { date: "Jul 15", label: "Estate planning consult", tone: "gold" },
  { date: "Jul 22", label: "Portfolio rebalance review", tone: "navy" },
  { date: "Jul 30", label: "Quarterly report sent", tone: "muted" },
] as const;

function Timeline() {
  return (
    <div className="relative pt-2">
      <div className="absolute left-0 right-0 top-[26px] h-px" style={{ background: BORDER }} />
      <div className="relative grid grid-cols-6 gap-4">
        {TIMELINE.map((step) => (
          <div key={step.date} className="flex flex-col items-start">
            <div
              className="relative z-10 mb-3 mt-3 h-3 w-3 rounded-full"
              style={{
                background: step.tone === "gold" ? GOLD : step.tone === "navy" ? "#141E55" : "#D1D5DB",
                boxShadow: `0 0 0 4px ${CARD_BG}`,
              }}
            />
            <div className="text-[11px] font-mono uppercase tracking-wider tabular" style={{ color: MUTED }}>{step.date}</div>
            <div className="mt-1 text-sm font-medium leading-snug" style={{ color: TEXT }}>{step.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

const SENTIMENT_BANDS = [
  { from: 0, to: 8, tone: "pos" },
  { from: 8, to: 14, tone: "neu" },
  { from: 14, to: 22, tone: "neg" },
  { from: 22, to: 32, tone: "neu" },
  { from: 32, to: 42, tone: "pos" },
  { from: 42, to: 47, tone: "pos" },
] as const;

const TONE_COLOR = {
  pos: "#16A34A",
  neu: "#D97706",
  neg: "#DC2626",
} as const;

const SENTIMENT_PEAKS = [
  { at: "00:02", label: "Engaged — portfolio discussion", tone: "pos" as const, pct: (2 / 47) * 100 },
  { at: "00:18", label: "Concerned — macro uncertainty", tone: "neu" as const, pct: (18 / 47) * 100 },
  { at: "00:38", label: "Positive — estate planning resolution", tone: "pos" as const, pct: (38 / 47) * 100 },
];

function SentimentBlock() {
  return (
    <div className="grid grid-cols-12 gap-6">
      <div className="col-span-12 lg:col-span-8 space-y-5">
        <div>
          <div className="mb-3 flex items-center justify-between text-[11px]" style={{ color: MUTED }}>
            <span>00:00</span>
            <span>Sentiment across call duration</span>
            <span>47:00</span>
          </div>
          <div className="relative w-full pt-6">
            {/* dot markers above the bar */}
            {SENTIMENT_PEAKS.map((p) => (
              <div
                key={p.at + "-dot"}
                className="group absolute -top-0.5 -translate-x-1/2"
                style={{ left: `${p.pct}%` }}
              >
                <span
                  className="block h-2 w-2 rounded-full ring-2 ring-white"
                  style={{ background: TONE_COLOR[p.tone], boxShadow: "0 1px 4px rgba(10,18,64,0.15)" }}
                />
                <div
                  className="pointer-events-none absolute left-1/2 top-full z-10 mt-1 hidden -translate-x-1/2 whitespace-nowrap rounded-md px-2 py-1 text-[10px] text-white shadow-lg group-hover:block"
                  style={{ background: NAVY }}
                >
                  {p.at} · {p.label}
                </div>
              </div>
            ))}
            {/* thin gradient bar */}
            <div
              className="relative h-[6px] w-full overflow-hidden rounded-full"
              style={{
                background:
                  "linear-gradient(90deg, #16A34A 0%, #4ADE80 18%, #D97706 38%, #DC2626 50%, #D97706 62%, #4ADE80 82%, #16A34A 100%)",
              }}
            />
          </div>
          <div className="mt-4 flex gap-4 text-[11px]" style={{ color: MUTED }}>
            <Legend color={TONE_COLOR.pos} label="Positive" />
            <Legend color={TONE_COLOR.neu} label="Neutral" />
            <Legend color={TONE_COLOR.neg} label="Concerned" />
          </div>
        </div>
        <ul className="space-y-2.5">
          {SENTIMENT_PEAKS.map((p) => (
            <li
              key={p.at}
              className="flex items-center gap-3 p-3"
              style={{ background: "#FAFAF9", border: "1px solid rgba(20,30,85,0.06)", borderRadius: 12 }}
            >
              <span className="h-2 w-2 rounded-full" style={{ background: TONE_COLOR[p.tone] }} />
              <span className="font-mono text-[12px] tabular" style={{ color: MUTED }}>{p.at}</span>
              <span className="text-sm" style={{ color: TEXT }}>{p.label}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">
        <div
          className="flex items-center gap-4 p-5"
          style={{ background: "#FAFAF9", border: `1px solid ${BORDER}`, borderRadius: 16 }}
        >
          <BigRing value={78} />
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.18em]" style={{ color: GOLD }}>
              Overall sentiment
            </div>
            <div className="font-serif text-xl font-semibold" style={{ color: TEXT }}>78% Positive</div>
          </div>
        </div>
        <div
          className="p-5"
          style={{ background: "#FAFAF9", border: `1px solid ${BORDER}`, borderRadius: 16 }}
        >
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em]" style={{ color: GOLD }}>
            Client engagement
          </div>
          <div className="mt-1 flex items-center justify-between">
            <div className="font-serif text-xl font-semibold" style={{ color: TEXT }}>High</div>
            <div className="flex gap-1">
              {[0, 1, 2, 3, 4].map((i) => (
                <span
                  key={i}
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ background: i < 4 ? GOLD : "#E5E7EB" }}
                />
              ))}
            </div>
          </div>
          <div className="mt-1 text-[11px]" style={{ color: MUTED }}>4 / 5</div>
        </div>
      </div>
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

function BigRing({ value }: { value: number }) {
  const r = 27, c = 2 * Math.PI * r, off = c * (1 - value / 100);
  return (
    <div className="relative h-16 w-16">
      <svg viewBox="0 0 60 60" className="h-full w-full -rotate-90">
        <circle cx="30" cy="30" r={r} fill={PAGE_BG} stroke="#EDE9DD" strokeWidth="3" />
        <circle cx="30" cy="30" r={r} fill="none" stroke={GOLD} strokeWidth="3"
          strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-[13px] font-semibold tabular" style={{ color: NAVY }}>
        {value}%
      </div>
    </div>
  );
}

const SUGGESTIONS: { chip: string; response: string }[] = [
  {
    chip: "Summarize client's risk concerns",
    response:
      "Mr. Ferretti raised two principal risk concerns during the call: (1) macroeconomic uncertainty driving his interest in a 5–8% gold allocation as a hedge, and (2) geographic concentration in European assets, which he aims to offset through UAE real estate exposure. Liquidity needs remain moderate; his risk tolerance has shifted from Conservative to Moderate-Conservative since the March 2026 review.",
  },
  {
    chip: "Draft follow-up email to Mr. Ferretti",
    response:
      "Subject: Following up on today's call — gold, Dubai, and estate planning\n\nDear Alessandro,\n\nThank you for the productive conversation this morning. As agreed, I will prepare a proposal for a 5–8% gold allocation (physical + ETF split) and circulate a shortlist of Dubai Marina and Palm Jumeirah residential opportunities by July 2. I have also requested an estate-planning slot with our wealth structuring team before mid-July.\n\nWarm regards,\nSofia",
  },
  {
    chip: "Compare gold allocation vs client benchmark",
    response:
      "Current gold exposure: 1.8% of liquid assets (~CHF 76K). Proposed target: 6% (~CHF 252K), a CHF 176K increase. JB Moderate-Conservative benchmark recommends 4–7% precious metals in the current macro regime, so the proposed allocation sits at the upper end of guidance but remains within model bounds.",
  },
  {
    chip: "What estate planning actions are urgent?",
    response:
      "Three items require attention before year-end: (1) update the family trust deed to reflect both children as adult beneficiaries, (2) review the Italian/Swiss cross-border succession structure given recent regulatory changes, and (3) refresh beneficiary designations on the Lombard credit facility. A consultation with the wealth structuring team is scheduled for July 15.",
  },
];

function AIChat() {
  const [value, setValue] = useState("");
  const [response, setResponse] = useState<string | null>(null);

  const submit = (q: string) => {
    const found = SUGGESTIONS.find((s) => s.chip === q);
    setResponse(found ? found.response : `Looking into: "${q}" — analysis would appear here based on the full call transcript and client history.`);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.chip}
            onClick={() => { setValue(s.chip); submit(s.chip); }}
            className="press rounded-full border px-3 py-1.5 text-xs font-medium hover:bg-[#FAFAF7]"
            style={{ borderColor: GOLD + "55", background: GOLD + "12", color: "#6E5424" }}
          >
            {s.chip}
          </button>
        ))}
      </div>
      <form
        onSubmit={(e) => { e.preventDefault(); if (value.trim()) submit(value.trim()); }}
        className="flex items-center gap-2 p-2"
        style={{ background: "#FFFFFF", border: `1px solid ${BORDER}`, borderRadius: 16, boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}
      >
        <MessageSquare className="ml-2 h-4 w-4" style={{ color: MUTED }} />
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="e.g. What was the client's main concern about gold exposure?"
          className="flex-1 bg-transparent px-2 py-2 text-sm outline-none"
          style={{ color: TEXT }}
        />
        <button
          type="submit"
          className="press flex h-9 w-9 items-center justify-center rounded-xl text-white"
          style={{ background: "#141E55" }}
          aria-label="Send"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
      {response && (
        <div
          className="animate-fade-up p-5"
          style={{
            background: "#FFFFFF",
            border: `1px solid ${BORDER}`,
            borderLeft: `4px solid ${GOLD}`,
            borderRadius: 12,
            color: TEXT,
            whiteSpace: "pre-wrap",
          }}
        >
          <div className="mb-2 inline-flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em]" style={{ color: GOLD }}>
            <Sparkles className="h-3 w-3" /> Intelligence Assistant
          </div>
          <div className="text-sm leading-relaxed">{response}</div>
        </div>
      )}
    </div>
  );
}

function NewsCard({
  tag, source, time, title, summary,
}: { tag: string; source: string; time: string; title: string; summary: string }) {
  return (
    <article
      className="press flex h-full flex-col gap-3 p-4"
      style={{ background: "#FAFAF9", border: "1px solid rgba(20,30,85,0.06)", borderRadius: 14 }}
    >
      <div className="flex items-center justify-between">
        <span
          className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
          style={{ background: GOLD + "1A", color: "#8a6f29", border: `1px solid ${GOLD}55` }}
        >
          {tag}
        </span>
        <span className="text-[11px]" style={{ color: MUTED }}>{time}</span>
      </div>
      <h3 className="text-sm font-semibold leading-snug" style={{ color: NAVY }}>{title}</h3>
      <p className="flex-1 text-[13px] leading-relaxed" style={{ color: BODY }}>{summary}</p>
      <div className="flex items-center justify-between border-t pt-2.5" style={{ borderColor: BORDER }}>
        <span className="text-[11px] font-medium" style={{ color: MUTED }}>{source}</span>
        <button
          onClick={() => toast("Opening article", { description: source })}
          className="press inline-flex items-center gap-1 text-[11px] font-medium"
          style={{ color: NAVY }}
        >
          Read <ExternalLink className="h-3 w-3" />
        </button>
      </div>
    </article>
  );
}
