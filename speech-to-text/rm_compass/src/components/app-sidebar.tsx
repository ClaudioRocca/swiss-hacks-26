import { Link, useRouterState } from "@tanstack/react-router";
import { Radio, LayoutDashboard, Phone, ListChecks, FileText } from "lucide-react";
import { useCallState } from "../lib/call-state";

const nav = [
  { to: "/", label: "Live Call", icon: Radio },
  { to: "/post-call", label: "Post-Call Dashboard", icon: LayoutDashboard },
] as const;

const SECTION_LABEL = "text-[9px] font-medium uppercase tracking-[0.2em]";

export function AppSidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { callEnded } = useCallState();

  return (
    <aside
      className="flex h-screen w-64 shrink-0 flex-col text-white"
      style={{
        background: "linear-gradient(180deg, #0A1240 0%, #141E55 100%)",
        borderRight: "1px solid rgba(255,255,255,0.05)",
      }}
    >
      <div
        className="flex flex-col gap-6 px-7 pt-8 pb-6"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        {/* Brand */}
        <div className="flex items-center gap-4">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg font-serif text-xl font-bold text-white"
            style={{
              background: "linear-gradient(135deg, #B8955A, #92681F)",
              boxShadow: "0 4px 16px rgba(184,149,90,0.35)",
            }}
          >
            JB
          </div>
          <div className="min-w-0">
            <div
              className="truncate font-serif text-[18px] font-semibold text-white"
              style={{ letterSpacing: "0.14em", lineHeight: 1.3 }}
            >
              JULIUS BÄR
            </div>
            <div
              className="truncate text-[11px] font-medium uppercase tracking-[0.22em] text-white/50"
              style={{ lineHeight: 1.5, marginTop: 2 }}
            >
              RM Intelligence
            </div>
          </div>
        </div>

        {/* RM Profile */}
        <div
          className="flex items-center gap-3.5 rounded-xl px-4 py-3"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.07)",
          }}
        >
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white"
            style={{
              background: "linear-gradient(135deg, #B8955A, #92681F)",
            }}
          >
            SL
          </div>
          <div className="min-w-0">
            <div className="truncate text-[14px] font-semibold text-white/95">
              Sofia Lambro
            </div>
            <div className="truncate text-[12px] text-white/45">
              Senior RM · Zürich
            </div>
          </div>
        </div>
      </div>

      <div className={"px-5 pb-2 text-white/30 " + SECTION_LABEL}>Navigation</div>
      <nav className="flex flex-col gap-1 px-3">
        {nav.map((item) => {
          const active = pathname === item.to;
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className="press group relative flex items-center gap-3 overflow-hidden px-3 py-2.5 text-sm transition-colors"
              style={{
                background: active ? "rgba(184,149,90,0.12)" : "transparent",
                borderLeft: active ? "2px solid #B8955A" : "2px solid transparent",
                borderRadius: 10,
                color: active ? "#fff" : "rgba(255,255,255,0.7)",
              }}
            >
              <Icon className="h-4 w-4" strokeWidth={1.6} />
              <span className="font-medium">{item.label}</span>
              {active && item.to === "/" && !callEnded && (
                <span className="ml-auto h-1.5 w-1.5 animate-blink rounded-full bg-danger" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className={"px-5 pt-7 pb-2 text-white/30 " + SECTION_LABEL}>Client</div>
      <Link
        to="/client"
        className="press mx-3 block p-4 transition-colors hover:bg-white/[0.08]"
        style={{
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 12,
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold text-white"
            style={{
              background: "linear-gradient(135deg, #B8955A, #92681F)",
              boxShadow: "0 4px 12px rgba(184,149,90,0.35)",
            }}
          >
            AF
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-medium text-white">Dr. M. Keller</div>
            <div className="flex items-center gap-1.5 text-[11px] text-white/60">
              <span className={"h-1.5 w-1.5 rounded-full " + (callEnded ? "bg-white/40" : "animate-blink bg-danger")} />
              {callEnded ? "Call ended" : "Active call"}
            </div>
          </div>
        </div>
        <div className="mt-3 flex items-baseline justify-between border-t border-white/10 pt-3">
          <span className="text-[10px] uppercase tracking-wider text-white/50">AUM</span>
          <span className="font-serif text-base tabular" style={{ color: "#B8955A" }}>CHF 4.2M</span>
        </div>
      </Link>

      <div className={"px-5 pt-7 pb-2 text-white/30 " + SECTION_LABEL}>Quick Stats</div>
      <div className="mx-3 space-y-1">
        <Stat to="/calls-today" icon={Phone} label="Calls today" value="3" />
        <Stat to="/action-items" icon={ListChecks} label="Action items pending" value="7" />
        <Stat to="/proposals" icon={FileText} label="Proposals sent" value="2" />
      </div>

      <div className="flex-1" />
    </aside>
  );
}

function Stat({
  to,
  icon: Icon,
  label,
  value,
}: {
  to: "/calls-today" | "/action-items" | "/proposals";
  icon: typeof Phone;
  label: string;
  value: string;
}) {
  return (
    <Link
      to={to}
      className="press flex cursor-pointer items-center gap-3 px-3 py-2 transition-colors hover:bg-white/[0.04]"
      style={{ borderRadius: 8 }}
    >
      <div
        className="flex h-7 w-7 items-center justify-center rounded-md text-white/70"
        style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}
      >
        <Icon className="h-3.5 w-3.5" strokeWidth={1.7} />
      </div>
      <div className="flex-1 text-[12px]" style={{ color: "rgba(255,255,255,0.5)" }}>{label}</div>
      <div className="font-serif text-base font-semibold text-white tabular">{value}</div>
    </Link>
  );
}
