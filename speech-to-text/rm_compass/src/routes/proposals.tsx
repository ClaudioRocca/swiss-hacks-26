import { createFileRoute } from "@tanstack/react-router";
import { FileText } from "lucide-react";
import { SubPageShell, SHELL_CONSTANTS as C } from "../components/sub-page-shell";

export const Route = createFileRoute("/proposals")({
  head: () => ({ meta: [{ title: "Proposals Sent" }] }),
  component: ProposalsPage,
});

const PROPOSALS = [
  {
    title: "Gold Allocation Proposal",
    client: "Dr. Maximilian Keller",
    amount: "CHF 210,000",
    sent: "Jun 20, 2026 · 11:48",
    status: "Awaiting client review",
    tag: "Precious Metals",
  },
  {
    title: "Structured Note — EUR/USD",
    client: "Mrs. Helena Brunner",
    amount: "CHF 480,000",
    sent: "Jun 19, 2026 · 16:02",
    status: "Reviewed · negotiation",
    tag: "Structured Products",
  },
];

function ProposalsPage() {
  return (
    <SubPageShell eyebrow="Pipeline" title="Proposals Sent" subtitle="2 active proposals">
      <div className="grid grid-cols-2 gap-6">
        {PROPOSALS.map((p) => (
          <article key={p.title} className="p-6" style={{ background: C.CARD, border: `1px solid ${C.BORDER}`, borderRadius: 16 }}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl" style={{ background: C.GOLD + "1A", color: C.GOLD, border: `1px solid ${C.GOLD}55` }}>
                <FileText className="h-4 w-4" />
              </div>
              <span className="rounded-full border px-2.5 py-0.5 text-[11px] font-medium" style={{ borderColor: C.BORDER, background: C.SOFT, color: C.MUTED }}>
                {p.tag}
              </span>
            </div>
            <h2 className="mt-4 font-serif text-xl" style={{ color: C.TEXT }}>{p.title}</h2>
            <div className="mt-1 text-sm" style={{ color: C.MUTED }}>{p.client}</div>

            <div className="mt-5 grid grid-cols-2 gap-4 border-t pt-4" style={{ borderColor: C.BORDER }}>
              <div>
                <div className="text-[11px] uppercase tracking-wider" style={{ color: C.MUTED }}>Amount</div>
                <div className="mt-0.5 font-serif text-lg tabular" style={{ color: C.TEXT }}>{p.amount}</div>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-wider" style={{ color: C.MUTED }}>Sent</div>
                <div className="mt-0.5 text-sm" style={{ color: C.TEXT }}>{p.sent}</div>
              </div>
            </div>
            <div className="mt-4 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-medium" style={{ borderColor: C.GOLD + "66", background: C.GOLD + "1A", color: "#8a6f29" }}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: C.GOLD }} />
              {p.status}
            </div>
          </article>
        ))}
      </div>
    </SubPageShell>
  );
}
