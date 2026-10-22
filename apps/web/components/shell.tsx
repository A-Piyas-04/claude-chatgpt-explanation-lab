"use client";

/** Application shell: navigation plus the standing mode banners. */

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";
import { useQuery } from "@tanstack/react-query";

import { api, SystemStatus } from "@/lib/api";
import { Badge } from "./ui";

const NAV = [
  { href: "/", label: "Overview", hint: "Counts, coverage and spend" },
  { href: "/studio", label: "Experiment studio", hint: "Configure and run experiments" },
  { href: "/compare", label: "Comparison", hint: "Read answers side by side" },
  { href: "/analysis", label: "Pedagogical analysis", hint: "Concepts and prerequisites" },
  { href: "/transform", label: "Transformation", hint: "Apply and inspect treatments" },
  { href: "/studies", label: "Human evaluation", hint: "Blinded comprehension studies" },
  { href: "/results", label: "Results", hint: "Compare conditions" },
  { href: "/library", label: "Library", hint: "Questions, prompts, strategies" },
];

export function useSystemStatus() {
  return useQuery({
    queryKey: ["status"],
    queryFn: () => api.get<SystemStatus>("status"),
    staleTime: 60_000,
  });
}

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data: status } = useSystemStatus();
  const [navOpen, setNavOpen] = React.useState(false);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1400px] items-center gap-3 px-4 py-2.5">
          <Link href="/" className="flex shrink-0 items-center gap-2">
            <span
              aria-hidden
              className="grid h-6 w-6 place-items-center rounded bg-accent text-[0.6875rem] font-bold text-white"
            >
              EL
            </span>
            <span className="text-sm font-semibold tracking-tight">ExplanationLab</span>
          </Link>

          <nav className="ml-2 hidden flex-1 items-center gap-0.5 lg:flex">
            {NAV.map((item) => {
              const active =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={item.hint}
                  className={clsx(
                    "rounded-md px-2.5 py-1.5 text-xs font-medium transition",
                    active
                      ? "bg-accent-soft text-accent-strong"
                      : "text-ink-muted hover:bg-canvas hover:text-ink",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            {status?.demo_mode ? (
              <Badge tone="synthetic" title={status.demo_mode_notice ?? undefined}>
                Demo mode
              </Badge>
            ) : (
              <Badge tone="success" title="Live provider credentials are configured.">
                Live
              </Badge>
            )}
            <button
              onClick={() => setNavOpen((open) => !open)}
              className="rounded-md border border-line-strong px-2 py-1 text-xs lg:hidden"
              aria-expanded={navOpen}
            >
              Menu
            </button>
          </div>
        </div>

        {navOpen ? (
          <nav className="border-t border-line bg-surface px-4 py-2 lg:hidden">
            <ul className="grid grid-cols-2 gap-1">
              {NAV.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setNavOpen(false)}
                    className="block rounded-md px-2.5 py-2 text-xs font-medium text-ink-muted hover:bg-canvas"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}
      </header>

      <main className="mx-auto max-w-[1400px] px-4 py-6">
        {status?.demo_mode ? (
          <div className="mb-5 rounded-lg border border-synthetic/30 bg-synthetic-soft px-4 py-3">
            <p className="text-sm font-semibold text-synthetic">
              Demo mode — generated content is synthetic
            </p>
            <p className="mt-1 text-xs leading-relaxed text-synthetic/90">
              No provider credentials are configured, so every generated explanation comes from
              local fixtures. Rows produced this way are flagged{" "}
              <span className="font-semibold">SYNTHETIC</span> for their whole lifetime and must
              never be reported as research findings. Add{" "}
              <code className="font-mono">OPENAI_API_KEY</code> or{" "}
              <code className="font-mono">ANTHROPIC_API_KEY</code> to{" "}
              <code className="font-mono">.env</code> and restart the API to run real experiments.
            </p>
          </div>
        ) : null}
        {children}
      </main>

      <footer className="mx-auto max-w-[1400px] px-4 pb-10 pt-4">
        <p className="border-t border-line pt-4 text-2xs leading-relaxed text-ink-faint">
          ExplanationLab keeps four kinds of evidence separate: automated diagnostics describe a
          text, an AI judge offers an opinion, participants report their perceptions, and only
          measured learner performance is treated as comprehension evidence. No screen in this
          application combines them into a single quality score.
        </p>
      </footer>
    </div>
  );
}
