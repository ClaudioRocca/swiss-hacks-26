import { useRouter } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import type { ReactNode } from "react";

export function SubPageShell({
  eyebrow, title, subtitle, children,
}: { eyebrow?: string; title: string; subtitle?: string; children: ReactNode }) {
  const router = useRouter();
  return (
    <div className="min-h-screen bg-white" style={{ color: "#1A1A2E" }}>
      <header className="border-b px-10 py-6" style={{ borderColor: "#E5E7EB", background: "#FAFAFA" }}>
        <button
          onClick={() => {
            if (typeof window !== "undefined" && window.history.length > 1) router.history.back();
            else router.navigate({ to: "/" });
          }}
          className="press mb-3 inline-flex items-center gap-1.5 text-sm font-medium hover:opacity-70"
          style={{ color: "#6B7280" }}
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        {eyebrow && (
          <div className="text-[11px] uppercase tracking-[0.18em]" style={{ color: "#C9A84C" }}>
            {eyebrow}
          </div>
        )}
        <h1 className="mt-1 font-serif text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm" style={{ color: "#6B7280" }}>{subtitle}</p>}
      </header>
      <div className="px-10 py-8 max-w-[1200px]">{children}</div>
    </div>
  );
}

export const SHELL_CONSTANTS = {
  TEXT: "#1A1A2E",
  MUTED: "#6B7280",
  BORDER: "#E5E7EB",
  CARD: "#FFFFFF",
  SOFT: "#F3F4F6",
  GOLD: "#C9A84C",
  NAVY: "#141E55",
};
