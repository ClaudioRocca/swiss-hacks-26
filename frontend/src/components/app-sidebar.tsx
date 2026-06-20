import { Link, useRouterState } from "@tanstack/react-router";
import { Radio, LayoutDashboard, Phone, ListChecks, FileText } from "lucide-react";
import { useCallState } from "../lib/call-state";

// Julius Bär palette
const INK = "#141E55";       // navy
const LINE = "#E7E4DB";      // hairline
const STONE = "#F4F3EE";     // warm light-gray panel
const MUTE = "#7A7D88";      // secondary text

const nav = [
  { to: "/", label: "Live Call", icon: Radio },
  { to: "/post-call", label: "Post-Call Dashboard", icon: LayoutDashboard },
] as const;

const SECTION_LABEL = "text-[9px] font-medium uppercase tracking-[0.22em]";

export function AppSidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { callEnded } = useCallState();

  return (
    <aside
      className="flex w-64 shrink-0 flex-col"
      style={{ background: "#FFFFFF", borderRight: `1px solid ${LINE}`, color: INK }}
    >
      <div className="flex flex-col gap-6 px-7 pt-8 pb-6" style={{ borderBottom: `1px solid ${LINE}` }}>
        {/* Brand */}
        <div>
          <div className="font-serif" style={{ color: INK, fontSize: 24, fontWeight: 600, letterSpacing: "0.01em", lineHeight: 1.1 }}>
            Julius Bär
          </div>
          <div className={SECTION_LABEL} style={{ color: MUTE, marginTop: 6 }}>
            RM Intelligence
          </div>
        </div>

        {/* RM Profile */}
        <div className="flex items-center gap-3.5 rounded-xl px-4 py-3" style={{ background: STONE }}>
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white"
            style={{ background: INK }}
          >
            SL
          </div>
          <div className="min-w-0">
            <div className="truncate text-[14px] font-semibold" style={{ color: INK }}>Sofia Lambro</div>
            <div className="truncate text-[12px]" style={{ color: MUTE }}>Senior RM · Zürich</div>
          </div>
        </div>
      </div>

      <div className={"px-5 pb-2 " + SECTION_LABEL} style={{ color: MUTE, paddingTop: 24 }}>Navigation</div>
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
                background: active ? STONE : "transparent",
                borderLeft: active ? `2px solid ${INK}` : "2px solid transparent",
                borderRadius: 8,
                color: active ? INK : MUTE,
                fontWeight: active ? 600 : 500,
              }}
            >
              <Icon className="h-4 w-4" strokeWidth={1.6} />
              <span>{item.label}</span>
              {active && item.to === "/" && !callEnded && (
                <span className="ml-auto h-1.5 w-1.5 animate-blink rounded-full" style={{ background: "#D4351C" }} />
              )}
            </Link>
          );
        })}
      </nav>

      <div className={"px-5 pb-2 " + SECTION_LABEL} style={{ color: MUTE, paddingTop: 28 }}>Client</div>
      <Link
        to="/client"
        className="press mx-3 block p-4 transition-colors"
        style={{ background: STONE, borderRadius: 12 }}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold text-white" style={{ background: INK }}>
            MK
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-medium" style={{ color: INK }}>Dr. M. Keller</div>
            <div className="flex items-center gap-1.5 text-[11px]" style={{ color: MUTE }}>
              <span className={"h-1.5 w-1.5 rounded-full " + (callEnded ? "" : "animate-blink")} style={{ background: callEnded ? "#C3C0B6" : "#D4351C" }} />
              {callEnded ? "Call ended" : "Active call"}
            </div>
          </div>
        </div>
        <div className="mt-3 flex items-baseline justify-between pt-3" style={{ borderTop: `1px solid ${LINE}` }}>
          <span className="text-[10px] uppercase tracking-wider" style={{ color: MUTE }}>AUM</span>
          <span className="font-serif text-base tabular" style={{ color: INK }}>CHF 47.5M</span>
        </div>
      </Link>

      <div className={"px-5 pb-2 " + SECTION_LABEL} style={{ color: MUTE, paddingTop: 28 }}>Quick Stats</div>
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
      className="press flex cursor-pointer items-center gap-3 px-3 py-2 transition-colors"
      style={{ borderRadius: 8 }}
    >
      <div className="flex h-7 w-7 items-center justify-center rounded-md" style={{ background: STONE, color: INK }}>
        <Icon className="h-3.5 w-3.5" strokeWidth={1.7} />
      </div>
      <div className="flex-1 text-[12px]" style={{ color: MUTE }}>{label}</div>
      <div className="font-serif text-base font-semibold tabular" style={{ color: INK }}>{value}</div>
    </Link>
  );
}
