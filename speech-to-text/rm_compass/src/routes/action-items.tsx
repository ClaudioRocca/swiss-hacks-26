import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { SubPageShell, SHELL_CONSTANTS as C } from "../components/sub-page-shell";

export const Route = createFileRoute("/action-items")({
  head: () => ({ meta: [{ title: "Action Items" }] }),
  component: ActionItemsPage,
});

const PRIORITY = {
  HIGH: { pill: { bg: "#FEE2E2", text: "#B91C1C", border: "#FCA5A5" }, bar: "#DC2626" },
  MED: { pill: { bg: "#FEF3C7", text: "#92400E", border: "#FCD34D" }, bar: "#D97706" },
  LOW: { pill: { bg: "#DCFCE7", text: "#166534", border: "#86EFAC" }, bar: "#16A34A" },
} as const;

const ITEMS: Array<{ priority: keyof typeof PRIORITY; text: string; client: string; due: string }> = [
  { priority: "HIGH", text: "Prepare gold allocation proposal (5–8% portfolio)", client: "A. Ferretti", due: "Jun 24" },
  { priority: "HIGH", text: "Schedule Dubai property viewing — Q3 2026", client: "A. Ferretti", due: "Jul 02" },
  { priority: "HIGH", text: "Review margin facility renewal terms", client: "H. Brunner", due: "Jun 25" },
  { priority: "MED", text: "Book estate planning consultation with legal team", client: "A. Ferretti", due: "Jul 15" },
  { priority: "MED", text: "Send Q2 macro outlook deck", client: "Y. Demir", due: "Jul 05" },
  { priority: "MED", text: "Confirm KYC refresh signatures", client: "H. Brunner", due: "Jul 08" },
  { priority: "LOW", text: "Send quarterly performance report", client: "A. Ferretti", due: "Jul 30" },
];

function ActionItemsPage() {
  return (
    <SubPageShell eyebrow="Pending" title="Action Items" subtitle="7 items pending across 3 clients">
      <ul className="space-y-3">
        {ITEMS.map((it, i) => <Row key={i} {...it} />)}
      </ul>
    </SubPageShell>
  );
}

function Row({
  priority, text, client, due,
}: { priority: keyof typeof PRIORITY; text: string; client: string; due: string }) {
  const [done, setDone] = useState(false);
  const p = PRIORITY[priority];
  return (
    <li
      className="press relative flex items-start gap-3 overflow-hidden p-4 pl-5"
      style={{ background: C.CARD, border: `1px solid ${C.BORDER}`, borderRadius: 12 }}
    >
      <span className="absolute left-0 top-0 h-full w-[3px]" style={{ background: p.bar }} />
      <button
        onClick={() => setDone((d) => !d)}
        aria-label="Toggle complete"
        className="press mt-0.5 flex h-4 w-4 items-center justify-center rounded border"
        style={{
          background: done ? C.GOLD : C.CARD,
          borderColor: done ? C.GOLD : "#D1D5DB",
          color: done ? "#1A1A2E" : "transparent",
        }}
      >
        {done && <CheckCircle2 className="h-3 w-3" strokeWidth={3} />}
      </button>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded border px-1.5 py-0.5 text-[10px] font-semibold tracking-wide"
            style={{ background: p.pill.bg, color: p.pill.text, borderColor: p.pill.border }}>
            {priority}
          </span>
          <span className="text-sm" style={{ color: C.TEXT, textDecoration: done ? "line-through" : "none", opacity: done ? 0.5 : 1 }}>
            {text}
          </span>
        </div>
        <div className="mt-1.5 text-[11px]" style={{ color: C.MUTED }}>
          {client} · Due {due}
        </div>
      </div>
    </li>
  );
}
