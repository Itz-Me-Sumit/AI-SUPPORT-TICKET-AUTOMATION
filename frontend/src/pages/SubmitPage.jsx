import { useEffect, useRef, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, RotateCcw, Send, Sparkles } from "lucide-react";

import ResultCard from "../components/ResultCard";
import { createTicket } from "../lib/api";
import {
  BUTTON_PRIMARY,
  BUTTON_SECONDARY,
  CARD_CLASS,
  INPUT_CLASS,
  SAMPLE_TICKETS,
} from "../lib/constants";

const STAGES = [
  "Triaging the ticket",
  "Analysing the case",
  "Deciding the resolution",
  "Writing the customer reply",
];

const MAX_LENGTH = 5000;
const EMPTY_FORM = { customer_name: "", ticket: "", ticket_id: "" };

export default function SubmitPage() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const resultRef = useRef(null);

  // Move the progress indicator forward while the request is running.
  useEffect(() => {
    if (!loading) return undefined;
    setStage(0);
    const timer = setInterval(() => {
      setStage((current) => Math.min(current + 1, STAGES.length - 1));
    }, 5000);
    return () => clearInterval(timer);
  }, [loading]);

  // Scroll to the result when it arrives.
  useEffect(() => {
    if (result) {
      resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

  const canSubmit =
    form.customer_name.trim().length > 0 && form.ticket.trim().length >= 5 && !loading;

  const update = (field) => (event) =>
    setForm((current) => ({ ...current, [field]: event.target.value }));

  function applySample(sample) {
    setForm({ customer_name: sample.customer_name, ticket: sample.ticket, ticket_id: "" });
    setError("");
    setResult(null);
  }

  function handleReset() {
    setForm(EMPTY_FORM);
    setError("");
    setResult(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setError("");
    setResult(null);

    const payload = {
      customer_name: form.customer_name.trim(),
      ticket: form.ticket.trim(),
    };
    if (form.ticket_id.trim()) payload.ticket_id = form.ticket_id.trim();

    try {
      const data = await createTicket(payload);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Submit a support ticket</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Paste a customer message. The AI will classify it, analyse the case, decide the next
          step and draft a reply.
        </p>
      </div>

      <form onSubmit={handleSubmit} className={`${CARD_CLASS} space-y-4`}>
        <div>
          <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
            <Sparkles size={14} /> Try a sample ticket
          </p>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_TICKETS.map((sample) => (
              <button
                key={sample.label}
                type="button"
                disabled={loading}
                onClick={() => applySample(sample)}
                className="rounded-full border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 transition hover:border-indigo-400 hover:text-indigo-700 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:border-indigo-500 dark:hover:text-indigo-300"
              >
                {sample.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="customer_name" className="mb-1 block text-sm font-medium">
              Customer name
            </label>
            <input
              id="customer_name"
              type="text"
              maxLength={120}
              value={form.customer_name}
              onChange={update("customer_name")}
              placeholder="e.g. Rahul Sharma"
              className={INPUT_CLASS}
              disabled={loading}
            />
          </div>
          <div>
            <label htmlFor="ticket_id" className="mb-1 block text-sm font-medium">
              Ticket ID <span className="font-normal text-slate-500">(optional)</span>
            </label>
            <input
              id="ticket_id"
              type="text"
              maxLength={64}
              value={form.ticket_id}
              onChange={update("ticket_id")}
              placeholder="Auto-generated if empty"
              className={INPUT_CLASS}
              disabled={loading}
            />
          </div>
        </div>

        <div>
          <label htmlFor="ticket" className="mb-1 block text-sm font-medium">
            Ticket text
          </label>
          <textarea
            id="ticket"
            rows={6}
            maxLength={MAX_LENGTH}
            value={form.ticket}
            onChange={update("ticket")}
            placeholder="Describe the customer's problem..."
            className={INPUT_CLASS}
            disabled={loading}
          />
          <p className="mt-1 text-right text-xs text-slate-500 dark:text-slate-400">
            {form.ticket.length} / {MAX_LENGTH}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3">
          <button
            type="button"
            onClick={handleReset}
            disabled={loading}
            className={BUTTON_SECONDARY}
          >
            <RotateCcw size={16} /> Reset
          </button>
          <button type="submit" disabled={!canSubmit} className={BUTTON_PRIMARY}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            {loading ? "Processing..." : "Process ticket"}
          </button>
        </div>
      </form>

      {loading && (
        <div className={`${CARD_CLASS} fade-in`}>
          <p className="mb-3 text-sm font-medium">The AI is working on your ticket</p>
          <ul className="space-y-2">
            {STAGES.map((label, index) => {
              const done = index < stage;
              const active = index === stage;
              return (
                <li
                  key={label}
                  className={`flex items-center gap-2 text-sm ${
                    done || active
                      ? "text-slate-900 dark:text-slate-100"
                      : "text-slate-400 dark:text-slate-600"
                  }`}
                >
                  {done ? (
                    <CheckCircle2 size={16} className="text-emerald-500" />
                  ) : active ? (
                    <Loader2 size={16} className="animate-spin text-indigo-500" />
                  ) : (
                    <span className="inline-block h-4 w-4 rounded-full border border-current" />
                  )}
                  {label}
                </li>
              );
            })}
          </ul>
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            Free models can take up to a minute. Please keep this page open.
          </p>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="fade-in flex gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">Could not process the ticket</p>
            <p className="mt-1 break-words">{error}</p>
          </div>
        </div>
      )}

      <div ref={resultRef}>{result && <ResultCard ticket={result} />}</div>
    </div>
  );
}
