"use client";

/**
 * Small accessible component set.
 *
 * Hand-rolled rather than pulled from a component library, so the whole visual
 * system is one short file a solo maintainer can read. The pieces that carry
 * research meaning — SyntheticBadge, EvidenceLabel, StatValue, Caveat — exist
 * because the brief requires those distinctions to be visible wherever numbers
 * appear, not merely documented.
 */

import clsx from "clsx";
import React from "react";

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

export function Card({
  children,
  className,
  as: Tag = "div",
}: {
  children: React.ReactNode;
  className?: string;
  as?: keyof JSX.IntrinsicElements;
}) {
  return (
    <Tag className={clsx("rounded-lg border border-line bg-surface shadow-card", className)}>
      {children}
    </Tag>
  );
}

export function CardHeader({
  title,
  description,
  actions,
  className,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3",
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        {description ? (
          <p className="mt-0.5 text-xs text-ink-muted">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {eyebrow ? (
          <p className="mb-1 text-2xs font-semibold uppercase tracking-[0.14em] text-ink-faint">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{title}</h1>
        {description ? (
          <div className="mt-1.5 max-w-3xl text-sm text-ink-muted">{description}</div>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export function Section({
  title,
  description,
  children,
  className,
}: {
  title?: string;
  description?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={clsx("mb-8", className)}>
      {title ? (
        <div className="mb-3">
          <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
          {description ? <p className="mt-0.5 text-xs text-ink-muted">{description}</p> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Controls
// ---------------------------------------------------------------------------

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
  loading?: boolean;
};

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center gap-1.5 rounded-md border font-medium transition",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
        "disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm",
        variant === "primary" &&
          "border-accent bg-accent text-white hover:bg-accent-strong",
        variant === "secondary" &&
          "border-line-strong bg-surface text-ink hover:bg-canvas",
        variant === "ghost" && "border-transparent bg-transparent text-ink-muted hover:bg-canvas",
        variant === "danger" && "border-danger/30 bg-danger-soft text-danger hover:bg-danger/10",
        className,
      )}
    >
      {loading ? <Spinner /> : null}
      {children}
    </button>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={clsx("h-3.5 w-3.5 animate-spin", className)}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Field({
  label,
  hint,
  children,
  className,
  htmlFor,
}: {
  label: string;
  hint?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  htmlFor?: string;
}) {
  return (
    <div className={clsx("min-w-0", className)}>
      <label htmlFor={htmlFor} className="mb-1 block text-xs font-medium text-ink">
        {label}
      </label>
      {children}
      {hint ? <p className="mt-1 text-2xs leading-relaxed text-ink-faint">{hint}</p> : null}
    </div>
  );
}

const controlClasses =
  "w-full rounded-md border border-line-strong bg-surface px-2.5 py-1.5 text-sm text-ink " +
  "placeholder:text-ink-faint focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent " +
  "disabled:bg-canvas disabled:text-ink-faint";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...rest }, ref) {
    return <input ref={ref} {...rest} className={clsx(controlClasses, className)} />;
  },
);

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...rest }, ref) {
  return (
    <textarea
      ref={ref}
      {...rest}
      className={clsx(controlClasses, "font-sans leading-relaxed", className)}
    />
  );
});

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(function Select({ className, children, ...rest }, ref) {
  return (
    <select ref={ref} {...rest} className={clsx(controlClasses, "pr-8", className)}>
      {children}
    </select>
  );
});

export function Checkbox({
  label,
  description,
  checked,
  onChange,
  disabled,
}: {
  label: React.ReactNode;
  description?: React.ReactNode;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label
      className={clsx(
        "flex cursor-pointer items-start gap-2 text-sm",
        disabled && "cursor-not-allowed opacity-60",
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 shrink-0 rounded border-line-strong text-accent focus:ring-accent"
      />
      <span className="min-w-0">
        <span className="block leading-snug">{label}</span>
        {description ? (
          <span className="mt-0.5 block text-2xs leading-relaxed text-ink-faint">
            {description}
          </span>
        ) : null}
      </span>
    </label>
  );
}

// ---------------------------------------------------------------------------
// Status and meaning
// ---------------------------------------------------------------------------

export function Badge({
  children,
  tone = "neutral",
  className,
  title,
}: {
  children: React.ReactNode;
  tone?: "neutral" | "accent" | "warn" | "danger" | "synthetic" | "success";
  className?: string;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={clsx(
        "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-2xs font-medium",
        tone === "neutral" && "border-line-strong bg-canvas text-ink-muted",
        tone === "accent" && "border-accent/25 bg-accent-soft text-accent-strong",
        tone === "warn" && "border-warn/25 bg-warn-soft text-warn",
        tone === "danger" && "border-danger/25 bg-danger-soft text-danger",
        tone === "synthetic" && "border-synthetic/25 bg-synthetic-soft text-synthetic",
        tone === "success" && "border-accent/25 bg-accent-soft text-accent-strong",
        className,
      )}
    >
      {children}
    </span>
  );
}

/**
 * Demo-fixture marker. Appears everywhere a synthetic row surfaces, because
 * §8.3 requires demo data to be prominently labelled rather than quietly
 * mixed into results.
 */
export function SyntheticBadge({ className }: { className?: string }) {
  return (
    <Badge
      tone="synthetic"
      className={className}
      title="Produced by local demo fixtures, not a model. Carries no evidential value."
    >
      SYNTHETIC
    </Badge>
  );
}

const EVIDENCE_META: Record<
  string,
  { label: string; tone: "neutral" | "accent" | "warn" | "success"; help: string }
> = {
  automated_diagnostic: {
    label: "Automated diagnostic",
    tone: "neutral",
    help: "Deterministic surface measure. Describes the text; does not measure understanding.",
  },
  ai_judge_opinion: {
    label: "AI judge opinion",
    tone: "warn",
    help: "A judge model's rating. Subject to known biases; not comprehension evidence.",
  },
  human_preference: {
    label: "Human preference",
    tone: "accent",
    help: "Self-reported by participants. Perceived ease can diverge from actual understanding.",
  },
  human_comprehension: {
    label: "Human comprehension",
    tone: "success",
    help: "Measured learner performance. The primary evidence in this platform.",
  },
};

export function EvidenceLabel({
  evidenceClass,
  className,
}: {
  evidenceClass: string;
  className?: string;
}) {
  const meta = EVIDENCE_META[evidenceClass];
  if (!meta) return null;
  return (
    <Badge tone={meta.tone} className={className} title={meta.help}>
      {meta.label}
    </Badge>
  );
}

export function StatusDot({ status }: { status: string }) {
  const tone =
    status === "succeeded" || status === "completed" || status === "reported" || status === "open"
      ? "bg-accent"
      : status === "failed"
        ? "bg-danger"
        : status === "running" || status === "queued"
          ? "bg-warn animate-pulse"
          : "bg-line-strong";
  return <span className={clsx("inline-block h-1.5 w-1.5 rounded-full", tone)} aria-hidden />;
}

export function Caveat({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: "neutral" | "warn" | "danger" | "synthetic" | "accent";
  className?: string;
}) {
  return (
    <p
      className={clsx(
        "rounded-md border px-3 py-2 text-xs leading-relaxed",
        tone === "neutral" && "border-line bg-canvas text-ink-muted",
        tone === "warn" && "border-warn/25 bg-warn-soft text-warn",
        tone === "danger" && "border-danger/25 bg-danger-soft text-danger",
        tone === "synthetic" && "border-synthetic/25 bg-synthetic-soft text-synthetic",
        tone === "accent" && "border-accent/25 bg-accent-soft text-accent-strong",
        className,
      )}
    >
      {children}
    </p>
  );
}

export function Banner({
  tone = "warn",
  title,
  children,
}: {
  tone?: "warn" | "danger" | "synthetic" | "accent";
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div
      role="status"
      className={clsx(
        "mb-5 rounded-lg border px-4 py-3",
        tone === "warn" && "border-warn/30 bg-warn-soft",
        tone === "danger" && "border-danger/30 bg-danger-soft",
        tone === "synthetic" && "border-synthetic/30 bg-synthetic-soft",
        tone === "accent" && "border-accent/30 bg-accent-soft",
      )}
    >
      <p
        className={clsx(
          "text-sm font-semibold",
          tone === "warn" && "text-warn",
          tone === "danger" && "text-danger",
          tone === "synthetic" && "text-synthetic",
          tone === "accent" && "text-accent-strong",
        )}
      >
        {title}
      </p>
      {children ? (
        <div
          className={clsx(
            "mt-1 text-xs leading-relaxed",
            tone === "warn" && "text-warn/90",
            tone === "danger" && "text-danger/90",
            tone === "synthetic" && "text-synthetic/90",
            tone === "accent" && "text-accent-strong/90",
          )}
        >
          {children}
        </div>
      ) : null}
    </div>
  );
}

/**
 * A statistic with its uncertainty and sample size always attached.
 * There is no way to render a mean here without also rendering its n.
 */
export function StatValue({
  summary,
  format = (v) => v.toFixed(2),
  compact = false,
}: {
  summary: {
    n: number;
    mean: number | null;
    ci_low: number | null;
    ci_high: number | null;
    warnings?: string[];
  } | null;
  format?: (value: number) => string;
  compact?: boolean;
}) {
  if (!summary || summary.mean === null) {
    return <span className="text-ink-faint">—</span>;
  }
  const hasInterval = summary.ci_low !== null && summary.ci_high !== null;
  return (
    <span className="whitespace-nowrap" title={summary.warnings?.join(" ")}>
      <span className="font-medium tabular-nums">{format(summary.mean)}</span>
      {hasInterval ? (
        <span className="ml-1 text-2xs tabular-nums text-ink-faint">
          [{format(summary.ci_low!)}–{format(summary.ci_high!)}]
        </span>
      ) : (
        <span className="ml-1 text-2xs text-ink-faint">{compact ? "" : "(no interval)"}</span>
      )}
      <span className="ml-1 text-2xs text-ink-faint">n={summary.n}</span>
    </span>
  );
}

export function KeyValue({
  items,
  columns = 2,
}: {
  items: { label: string; value: React.ReactNode; hint?: string }[];
  columns?: 1 | 2 | 3;
}) {
  return (
    <dl
      className={clsx(
        "grid gap-x-6 gap-y-2.5 text-sm",
        columns === 1 && "grid-cols-1",
        columns === 2 && "grid-cols-1 sm:grid-cols-2",
        columns === 3 && "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
      )}
    >
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-2xs uppercase tracking-wide text-ink-faint" title={item.hint}>
            {item.label}
          </dt>
          <dd className="mt-0.5 break-words">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-line-strong bg-surface px-6 py-10 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      {children ? (
        <div className="mx-auto mt-1.5 max-w-md text-xs leading-relaxed text-ink-muted">
          {children}
        </div>
      ) : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="rounded-lg border border-danger/30 bg-danger-soft px-4 py-3">
      <p className="text-sm font-medium text-danger">Something went wrong</p>
      <p className="mt-1 break-words text-xs leading-relaxed text-danger/90">{message}</p>
      {retry ? (
        <Button size="sm" className="mt-3" onClick={retry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse rounded bg-line/70", className)} />;
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 px-1 py-6 text-sm text-ink-muted">
      <Spinner />
      {label}…
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tables, tabs, disclosure
// ---------------------------------------------------------------------------

export function Table({
  head,
  children,
  className,
}: {
  head: React.ReactNode[];
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("overflow-x-auto rounded-lg border border-line bg-surface", className)}>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-line bg-canvas">
            {head.map((cell, i) => (
              <th
                key={i}
                className="px-3 py-2 text-left text-2xs font-semibold uppercase tracking-wide text-ink-faint"
              >
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function Tr({
  children,
  className,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <tr
      onClick={onClick}
      className={clsx(
        "border-b border-line last:border-0",
        onClick && "cursor-pointer hover:bg-canvas",
        className,
      )}
    >
      {children}
    </tr>
  );
}

export function Td({
  children,
  className,
  colSpan,
}: {
  children: React.ReactNode;
  className?: string;
  colSpan?: number;
}) {
  return (
    <td colSpan={colSpan} className={clsx("px-3 py-2 align-top", className)}>
      {children}
    </td>
  );
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: string; label: string; count?: number }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="mb-4 flex flex-wrap gap-1 border-b border-line" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={clsx(
            "-mb-px rounded-t-md border-b-2 px-3 py-1.5 text-sm font-medium transition",
            active === tab.id
              ? "border-accent text-accent-strong"
              : "border-transparent text-ink-muted hover:text-ink",
          )}
        >
          {tab.label}
          {tab.count !== undefined ? (
            <span className="ml-1.5 text-2xs text-ink-faint">{tab.count}</span>
          ) : null}
        </button>
      ))}
    </div>
  );
}

export function Disclosure({
  summary,
  children,
  defaultOpen = false,
  className,
}: {
  summary: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
}) {
  return (
    <details
      open={defaultOpen}
      className={clsx("group rounded-md border border-line bg-surface", className)}
    >
      <summary className="cursor-pointer list-none px-3 py-2 text-xs font-medium text-ink-muted hover:text-ink">
        <span className="mr-1.5 inline-block transition group-open:rotate-90">▸</span>
        {summary}
      </summary>
      <div className="border-t border-line px-3 py-3">{children}</div>
    </details>
  );
}

export function Mono({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <code className={clsx("font-mono text-2xs text-ink-muted", className)}>{children}</code>
  );
}

export function ProgressBar({ done, total }: { done: number; total: number }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  return (
    <div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-line">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-1 text-2xs tabular-nums text-ink-faint">
        {done} / {total} ({pct}%)
      </p>
    </div>
  );
}

export function formatUsd(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (value === 0) return "$0.00";
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

export function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(1)} s`;
}

export function formatInt(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString();
}
