import { createFileRoute } from "@tanstack/react-router";
import { SubPageShell, SHELL_CONSTANTS as C } from "../components/sub-page-shell";

export const Route = createFileRoute("/client")({
  head: () => ({ meta: [{ title: "Client Profile — Ferretti" }] }),
  component: ClientProfilePage,
});

const ALLOC = [
  { label: "Equities", pct: 40, color: "#141E55" },
  { label: "Bonds", pct: 30, color: "#3B5BDB" },
  { label: "Alternatives", pct: 20, color: "#C9A84C" },
  { label: "Cash", pct: 10, color: "#9CA3AF" },
];

const INTERACTIONS = [
  { date: "Jun 20, 2026", type: "Call", note: "47-min portfolio review — gold, Dubai, estate" },
  { date: "May 14, 2026", type: "Meeting", note: "Quarterly in-person review at Milano office" },
  { date: "Apr 02, 2026", type: "Email", note: "Q1 performance summary delivered" },
];

function ClientProfilePage() {
  return (
    <SubPageShell eyebrow="Client Profile" title="Mr. Alessandro Ferretti" subtitle="Private wealth · Onboarded 2019">
      <div className="grid grid-cols-12 gap-6">
        <Card className="col-span-5">
          <SectionTitle>Overview</SectionTitle>
          <dl className="space-y-3 text-sm">
            <Field k="Full name" v="Alessandro Ferretti" />
            <Field k="AUM" v="CHF 4.2M" />
            <Field k="Risk profile" v="Moderate-Conservative" />
            <Field k="Residency" v="Milano, Italy" />
            <Field k="Relationship Manager" v="Sofia Lambro" />
          </dl>
        </Card>

        <Card className="col-span-7">
          <SectionTitle>Portfolio Breakdown</SectionTitle>
          <div className="flex items-center gap-8">
            <PieChart />
            <ul className="flex-1 space-y-2.5 text-sm">
              {ALLOC.map((a) => (
                <li key={a.label} className="flex items-center gap-3">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: a.color }} />
                  <span className="flex-1" style={{ color: C.TEXT }}>{a.label}</span>
                  <span className="font-serif tabular" style={{ color: C.TEXT }}>{a.pct}%</span>
                </li>
              ))}
            </ul>
          </div>
        </Card>

        <Card className="col-span-12">
          <SectionTitle>Last 3 Interactions</SectionTitle>
          <ul className="divide-y" style={{ borderColor: C.BORDER }}>
            {INTERACTIONS.map((it, i) => (
              <li key={i} className="grid grid-cols-[120px_100px_1fr] items-center gap-4 py-3 text-sm">
                <span className="font-mono text-[12px] tabular" style={{ color: C.MUTED }}>{it.date}</span>
                <span
                  className="inline-flex w-fit rounded-full border px-2.5 py-0.5 text-[11px] font-medium"
                  style={{ borderColor: C.BORDER, background: C.SOFT, color: C.TEXT }}
                >
                  {it.type}
                </span>
                <span style={{ color: C.TEXT }}>{it.note}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </SubPageShell>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section
      className={"p-6 " + className}
      style={{ background: C.CARD, border: `1px solid ${C.BORDER}`, borderRadius: 16 }}
    >
      {children}
    </section>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="mb-4 font-serif text-lg" style={{ color: C.TEXT }}>{children}</h2>;
}

function Field({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between border-b pb-2 last:border-0 last:pb-0" style={{ borderColor: C.BORDER }}>
      <dt className="text-[11px] uppercase tracking-wider" style={{ color: C.MUTED }}>{k}</dt>
      <dd className="font-medium" style={{ color: C.TEXT }}>{v}</dd>
    </div>
  );
}

function PieChart() {
  const size = 160;
  const r = 70;
  const cx = size / 2;
  const cy = size / 2;
  let cum = 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {ALLOC.map((a) => {
        const start = cum / 100;
        cum += a.pct;
        const end = cum / 100;
        const a0 = start * Math.PI * 2 - Math.PI / 2;
        const a1 = end * Math.PI * 2 - Math.PI / 2;
        const x0 = cx + r * Math.cos(a0);
        const y0 = cy + r * Math.sin(a0);
        const x1 = cx + r * Math.cos(a1);
        const y1 = cy + r * Math.sin(a1);
        const large = a.pct > 50 ? 1 : 0;
        return (
          <path
            key={a.label}
            d={`M${cx},${cy} L${x0},${y0} A${r},${r} 0 ${large} 1 ${x1},${y1} Z`}
            fill={a.color}
          />
        );
      })}
      <circle cx={cx} cy={cy} r={32} fill={C.CARD} />
    </svg>
  );
}
