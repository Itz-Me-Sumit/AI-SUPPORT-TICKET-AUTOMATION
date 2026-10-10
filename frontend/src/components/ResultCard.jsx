import { useState } from "react";
import { AlertTriangle, Bot, Check, Clock, Copy, UserCheck } from "lucide-react";

import Badge from "./Badge";
import {
  CARD_CLASS,
  CATEGORY_STYLES,
  PRIORITY_STYLES,
  RESOLUTION_STYLES,
  formatDate,
  humanize,
} from "../lib/constants";

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function Section({ title, children }) {
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {title}
      </h3>
      {children}
    </section>
  );
}

export function CaseAnalysis({ data }) {
  const entries = Object.entries(data || {});
  if (entries.length === 0) return null;

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {entries.map(([key, value]) => (
        <div
          key={key}
          className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950"
        >
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
            {humanize(key)}
          </p>
          <p className="mt-1 break-words text-sm">{formatValue(value)}</p>
        </div>
      ))}
    </div>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can be denied; nothing else to do.
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export default function ResultCard({ ticket }) {
  const failed = ticket.status === "failed";

  return (
    <div className={`${CARD_CLASS} fade-in space-y-6`}>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {ticket.ticket_id}
          </p>
          <h2 className="text-lg font-semibold">{ticket.customer_name}</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {formatDate(ticket.created_at)}
          </p>
        </div>

        {ticket.processing_ms != null && (
          <span className="inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
            <Clock size={14} />
            Processed in {(ticket.processing_ms / 1000).toFixed(1)}s
          </span>
        )}
      </header>

      <Section title="Original ticket">
        <p className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-950">
          {ticket.ticket_text}
        </p>
      </Section>

      {failed ? (
        <div className="flex gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">Processing failed</p>
            <p className="mt-1 break-words">{ticket.error || "Unknown error."}</p>
          </div>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            <Badge className={CATEGORY_STYLES[ticket.category] || CATEGORY_STYLES.general}>
              {humanize(ticket.category)}
            </Badge>
            <Badge className={PRIORITY_STYLES[ticket.priority] || PRIORITY_STYLES.low}>
              {humanize(ticket.priority)} priority
            </Badge>
            <Badge className="bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
              {ticket.language || "Unknown language"}
            </Badge>
            <Badge
              className={RESOLUTION_STYLES[ticket.resolution_type] || RESOLUTION_STYLES.resolve}
            >
              {humanize(ticket.resolution_type)}
            </Badge>
          </div>

          <Section title="Case analysis">
            <CaseAnalysis data={ticket.case_analysis} />
          </Section>

          <Section title="Resolution">
            <div
              className={`flex items-center gap-2 rounded-lg p-3 text-sm font-medium ${
                ticket.requires_human
                  ? "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                  : "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
              }`}
            >
              {ticket.requires_human ? <UserCheck size={18} /> : <Bot size={18} />}
              {ticket.requires_human ? "Human agent required" : "Handled automatically"}
            </div>
            <div className="space-y-2 text-sm">
              <p>
                <span className="font-medium">Recommended action: </span>
                {formatValue(ticket.recommended_action)}
              </p>
              <p className="text-slate-600 dark:text-slate-400">
                <span className="font-medium text-slate-900 dark:text-slate-100">Reason: </span>
                {formatValue(ticket.resolution_reason)}
              </p>
            </div>
          </Section>

          <Section title="Reply to customer">
            <div className="rounded-lg border border-indigo-200 bg-indigo-50/60 p-4 dark:border-indigo-900 dark:bg-indigo-950/40">
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{ticket.response}</p>
              <div className="mt-3 flex justify-end">
                <CopyButton text={ticket.response || ""} />
              </div>
            </div>
          </Section>
        </>
      )}
    </div>
  );
}
