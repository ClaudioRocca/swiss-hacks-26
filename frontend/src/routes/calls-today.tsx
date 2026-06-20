import { createFileRoute } from "@tanstack/react-router";
import { SubPageShell, SHELL_CONSTANTS as C } from "../components/sub-page-shell";

export const Route = createFileRoute("/calls-today")({
  head: () => ({ meta: [{ title: "Today's Calls" }] }),
  component: CallsTodayPage,
});

const CALLS = [
  { time: "09:15", client: "Mrs. Helena Brunner", duration: "32:14", status: "Completed" },
  { time: "11:00", client: "Dr. Maximilian Keller", duration: "47:02", status: "Active" },
  { time: "14:30", client: "Mr. Yusuf Demir", duration: "21:48", status: "Completed" },
];

function CallsTodayPage() {
  return (
    <SubPageShell eyebrow="Today" title="Today's Calls" subtitle="3 scheduled · 2 completed · 1 active">
      <div style={{ background: C.CARD, border: `1px solid ${C.BORDER}`, borderRadius: 16 }} className="overflow-hidden">
        <div className="grid grid-cols-[80px_1fr_120px_120px] gap-4 border-b px-5 py-3 text-[11px] font-medium uppercase tracking-[0.18em]" style={{ color: C.MUTED, borderColor: C.BORDER, background: "#FAFAFA" }}>
          <span>Time</span><span>Client</span><span>Duration</span><span>Status</span>
        </div>
        <ul className="divide-y" style={{ borderColor: C.BORDER }}>
          {CALLS.map((c) => {
            const active = c.status === "Active";
            return (
              <li key={c.time} className="grid grid-cols-[80px_1fr_120px_120px] items-center gap-4 px-5 py-4 text-sm" style={{ color: C.TEXT }}>
                <span className="font-mono tabular" style={{ color: C.MUTED }}>{c.time}</span>
                <span className="font-medium">{c.client}</span>
                <span className="tabular" style={{ color: C.MUTED }}>{c.duration}</span>
                <span>
                  <span
                    className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium"
                    style={
                      active
                        ? { borderColor: "#FCA5A5", background: "#FEE2E2", color: "#B91C1C" }
                        : { borderColor: "#86EFAC", background: "#DCFCE7", color: "#166534" }
                    }
                  >
                    <span className={"h-1.5 w-1.5 rounded-full " + (active ? "animate-blink" : "")} style={{ background: active ? "#DC2626" : "#16A34A" }} />
                    {c.status}
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </SubPageShell>
  );
}
