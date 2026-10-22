/**
 * Markdown renderer that builds React elements directly.
 *
 * Deliberately not a library, and deliberately not `dangerouslySetInnerHTML`.
 * Every string we render here is model-generated text from an untrusted
 * pipeline. Because this renderer only ever constructs React elements and
 * escapes text by construction, no markup in the source can execute — which is
 * a stronger guarantee than sanitising HTML after the fact (§11, §18).
 *
 * Supported: ATX headings, paragraphs, fenced code, blockquotes, ordered and
 * unordered lists, tables, horizontal rules, and inline code / bold / italic /
 * links. Raw HTML is rendered as literal text, never parsed.
 */

import React from "react";

type Block =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; text: string }
  | { type: "code"; language: string; lines: string[] }
  | { type: "quote"; lines: string[] }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "table"; header: string[]; rows: string[][] }
  | { type: "rule" };

const HEADING = /^(#{1,6})\s+(.*)$/;
const FENCE = /^```\s*([A-Za-z0-9_+-]*)\s*$/;
const UL_ITEM = /^\s*[-*+]\s+(.*)$/;
const OL_ITEM = /^\s*\d+[.)]\s+(.*)$/;
const QUOTE = /^>\s?(.*)$/;
const RULE = /^(-{3,}|\*{3,}|_{3,})\s*$/;
const TABLE_ROW = /^\s*\|(.+)\|\s*$/;
const TABLE_DIVIDER = /^\s*\|[\s:|-]+\|\s*$/;

function splitRow(line: string): string[] {
  const match = TABLE_ROW.exec(line);
  if (!match) return [];
  return match[1].split("|").map((cell) => cell.trim());
}

export function parseMarkdown(source: string): Block[] {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = FENCE.exec(line);
    if (fence) {
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !FENCE.test(lines[index])) {
        codeLines.push(lines[index]);
        index += 1;
      }
      index += 1; // closing fence
      blocks.push({ type: "code", language: fence[1] || "", lines: codeLines });
      continue;
    }

    if (RULE.test(line)) {
      blocks.push({ type: "rule" });
      index += 1;
      continue;
    }

    const heading = HEADING.exec(line);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2] });
      index += 1;
      continue;
    }

    if (QUOTE.test(line)) {
      const quoteLines: string[] = [];
      while (index < lines.length && QUOTE.test(lines[index])) {
        quoteLines.push(QUOTE.exec(lines[index])![1]);
        index += 1;
      }
      blocks.push({ type: "quote", lines: quoteLines });
      continue;
    }

    // Table: a pipe row followed by a divider row.
    if (TABLE_ROW.test(line) && index + 1 < lines.length && TABLE_DIVIDER.test(lines[index + 1])) {
      const header = splitRow(line);
      index += 2;
      const rows: string[][] = [];
      while (index < lines.length && TABLE_ROW.test(lines[index])) {
        rows.push(splitRow(lines[index]));
        index += 1;
      }
      blocks.push({ type: "table", header, rows });
      continue;
    }

    if (UL_ITEM.test(line) || OL_ITEM.test(line)) {
      const ordered = OL_ITEM.test(line);
      const items: string[] = [];
      while (index < lines.length) {
        const current = lines[index];
        const match = ordered ? OL_ITEM.exec(current) : UL_ITEM.exec(current);
        if (match) {
          items.push(match[1]);
          index += 1;
        } else if (current.trim() && /^\s{2,}\S/.test(current) && items.length) {
          // Continuation of the previous item.
          items[items.length - 1] += ` ${current.trim()}`;
          index += 1;
        } else {
          break;
        }
      }
      blocks.push({ type: "list", ordered, items });
      continue;
    }

    // Paragraph: consume until a blank line or the start of another block.
    const paragraph: string[] = [];
    while (index < lines.length) {
      const current = lines[index];
      if (
        !current.trim() ||
        HEADING.test(current) ||
        FENCE.test(current) ||
        RULE.test(current) ||
        QUOTE.test(current) ||
        UL_ITEM.test(current) ||
        OL_ITEM.test(current) ||
        TABLE_ROW.test(current)
      ) {
        break;
      }
      paragraph.push(current.trim());
      index += 1;
    }
    if (paragraph.length) {
      blocks.push({ type: "paragraph", text: paragraph.join(" ") });
    }
  }

  return blocks;
}

/** Inline formatting. Returns React nodes; never HTML. */
function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  // Order matters: code first so formatting inside backticks stays literal.
  const pattern =
    /(`[^`]+`)|(\*\*[^*]+\*\*)|(__[^_]+__)|(\*[^*\n]+\*)|(_[^_\n]+_)|(\[[^\]]+\]\([^)\s]+\))/g;

  let cursor = 0;
  let match: RegExpExecArray | null;
  let counter = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      nodes.push(text.slice(cursor, match.index));
    }
    const token = match[0];
    const key = `${keyPrefix}-i${counter++}`;

    if (token.startsWith("`")) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith("**") || token.startsWith("__")) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("[")) {
      const linkMatch = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(token);
      if (linkMatch) {
        const [, label, href] = linkMatch;
        // Only http(s) links are made clickable; anything else (javascript:,
        // data:, etc.) renders as plain text.
        if (/^https?:\/\//i.test(href)) {
          nodes.push(
            <a key={key} href={href} target="_blank" rel="noopener noreferrer nofollow">
              {label}
            </a>,
          );
        } else {
          nodes.push(<span key={key}>{label}</span>);
        }
      } else {
        nodes.push(token);
      }
    } else {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>);
    }
    cursor = match.index + token.length;
  }

  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
}

export function Markdown({
  source,
  variant = "reading",
  className = "",
}: {
  source: string;
  variant?: "reading" | "compact";
  className?: string;
}) {
  const blocks = React.useMemo(() => parseMarkdown(source ?? ""), [source]);
  const base = variant === "reading" ? "prose-reading" : "prose-compact";

  return (
    <div className={`${base} ${className}`}>
      {blocks.map((block, i) => {
        const key = `b${i}`;
        switch (block.type) {
          case "heading": {
            const Tag = (`h${Math.min(block.level, 6)}` as unknown) as keyof JSX.IntrinsicElements;
            return <Tag key={key}>{renderInline(block.text, key)}</Tag>;
          }
          case "paragraph":
            return <p key={key}>{renderInline(block.text, key)}</p>;
          case "code":
            return (
              <pre key={key}>
                <code>{block.lines.join("\n")}</code>
              </pre>
            );
          case "quote":
            return (
              <blockquote key={key}>
                {block.lines.map((line, j) => (
                  <p key={`${key}-q${j}`}>{renderInline(line, `${key}-q${j}`)}</p>
                ))}
              </blockquote>
            );
          case "list": {
            const Tag = block.ordered ? "ol" : "ul";
            return (
              <Tag key={key}>
                {block.items.map((item, j) => (
                  <li key={`${key}-l${j}`}>{renderInline(item, `${key}-l${j}`)}</li>
                ))}
              </Tag>
            );
          }
          case "table":
            return (
              <div key={key} className="overflow-x-auto">
                <table>
                  <thead>
                    <tr>
                      {block.header.map((cell, j) => (
                        <th key={`${key}-h${j}`}>{renderInline(cell, `${key}-h${j}`)}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {block.rows.map((row, j) => (
                      <tr key={`${key}-r${j}`}>
                        {row.map((cell, k) => (
                          <td key={`${key}-r${j}c${k}`}>
                            {renderInline(cell, `${key}-r${j}c${k}`)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          case "rule":
            return <hr key={key} />;
          default:
            return null;
        }
      })}
    </div>
  );
}

/** Renders a unified diff with per-line colouring. */
export function UnifiedDiff({ diff }: { diff: string }) {
  const lines = (diff ?? "").split("\n");
  return (
    <pre className="font-mono text-2xs leading-relaxed overflow-x-auto rounded-md border border-line bg-surface p-3">
      {lines.map((line, i) => {
        let cls = "";
        if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("@@")) {
          cls = "diff-line-meta";
        } else if (line.startsWith("+")) {
          cls = "diff-line-add";
        } else if (line.startsWith("-")) {
          cls = "diff-line-del";
        }
        return (
          <div key={i} className={`${cls} whitespace-pre-wrap break-words px-1`}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}
