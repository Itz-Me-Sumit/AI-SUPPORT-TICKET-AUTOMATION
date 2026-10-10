import { useCallback, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Download,
  Eye,
  FileJson,
  Loader2,
  Play,
  RotateCcw,
  SkipForward,
  Square,
  UploadCloud,
  XCircle,
} from "lucide-react";

import TicketModal from "../components/TicketModal";
import { createTicket } from "../lib/api";
import {
  BUTTON_PRIMARY,
  BUTTON_SECONDARY,
  CARD_CLASS,
  SAMPLE_TICKETS,
} from "../lib/constants";

const MAX_TICKETS = 50;

// Check the uploaded JSON and return clean ticket objects.
function validateTickets(raw) {
  if (!Array.isArray(raw) || raw.length === 0) {
    throw new Error("The file must contain a non-empty JSON array of tickets.");
  }
  if (raw.length > MAX_TICKETS) {
    throw new Error(`A maximum of ${MAX_TICKETS} tickets is allowed per upload.`);
  }

  const invalid = [];

  const tickets = raw.map((item, index) => {
    const name = typeof item?.customer_name === "string" ? item.customer_name.trim() : "";
    const text = typeof item?.ticket === "string" ? item.ticket.trim() : "";
    const id = typeof item?.ticket_id === "string" ? item.ticket_id.trim() : "";

    if (!name || text.length < 5) invalid.push(index + 1);

    return { customer_name: name, ticket: text, ...(id ? { ticket_id: id } : {}) };
  });

  if (invalid.length > 0) {
    throw new Error(
      `Invalid tickets at position ${invalid.slice(0, 10).join(", ")}. ` +
        'Each ticket needs a "customer_name" and a "ticket" text (at least 5 characters).'
    );
  }

  return tickets;
}

function downloadSample() {
  const sample = SAMPLE_TICKETS.slice(0, 3).map(({ customer_name, ticket }) => ({
    customer_name,
    ticket,
  }));
  const blob = new Blob([JSON.stringify(sample, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "sample_tickets.json";
  link.click();
  URL.revokeObjectURL(url);
}

function StatusCell({ row }) {
  switch (row.status) {
    case "processing":
      return (
        <span className="inline-flex items-center gap-1.5 text-indigo-600 dark:text-indigo-400">
          <Loader2 size={15} className="animate-spin" /> Processing
        </span>
      );
    case "done":
      return (
        <span className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 size={15} /> Done
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center gap-1.5 text-red-600 dark:text-red-400">
          <XCircle size={15} /> Failed
        </span>
      );
    case "skipped":
      return (
        <span className="inline-flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
          <SkipForward size={15} /> Skipped
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1.5 text-slate-400">
          <Circle size={15} /> Pending
        </span>
      );
  }
}

export default function BatchPage() {
  const [fileName, setFileName] = useState("");
  const [rows, setRows] = useState([]);
  const [parseError, setParseError] = useState("");
  const [running, setRunning] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [selected, setSelected] = useState(null);

  const cancelRef = useRef(false);
  const inputRef = useRef(null);

  const closeModal = useCallback(() => setSelected(null), []);

  const patchRow = (index, patch) =>
    setRows((current) =>
      current.map((row, position) => (position === index ? { ...row, ...patch } : row))
    );

  async function handleFile(file) {
    if (!file) return;

    setParseError("");
    setRows([]);
    setFileName(file.name);

    try {
      const raw = JSON.parse(await file.text());
      const tickets = validateTickets(raw);
      setRows(
        tickets.map((ticket) => ({ ...ticket, status: "pending", message: "", record: null }))
      );
    } catch (err) {
      setFileName("");
      setParseError(
        err instanceof SyntaxError ? "This file is not valid JSON." : err.message
      );
    }
  }

  function handleReset() {
    setRows([]);
    setFileName("");
    setParseError("");
    if (inputRef.current) inputRef.current.value = "";
  }

  async function handleRun() {
    // Only pending rows are processed, so Resume works after a Stop.
    const queue = rows
      .map((row, index) => ({ row, index }))
      .filter(({ row }) => row.status === "pending");

    if (queue.length === 0) return;

    cancelRef.current = false;
    setRunning(true);

    for (const { row, index } of queue) {
      if (cancelRef.current) break;

      patchRow(index, { status: "processing", message: "" });

      try {
        const payload = { customer_name: row.customer_name, ticket: row.ticket };
        if (row.ticket_id) payload.ticket_id = row.ticket_id;

        const record = await createTicket(payload);
        patchRow(index, { status: "done", record });
      } catch (err) {
        const duplicate = err.message.includes("already exists");
        patchRow(index, {
          status: duplicate ? "skipped" : "failed",
          message: err.message,
        });
      }
    }

    setRunning(false);
  }

  const counts = rows.reduce(
    (acc, row) => {
      acc[row.status] = (acc[row.status] || 0) + 1;
      return acc;
    },
    { pending: 0, processing: 0, done: 0, failed: 0, skipped: 0 }
  );

  const finished = rows.length - counts.pending - counts.processing;
  const percent = rows.length ? Math.round((finished / rows.length) * 100) : 0;
  const allFinished = rows.length > 0 && counts.pending === 0 && counts.processing === 0;
  const startedBefore = finished > 0;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Batch upload</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Upload a JSON file with many tickets. They are processed one by one so you can follow
          the progress.
        </p>
      </div>

      <div className={`${CARD_CLASS} space-y-4`}>
        <label
          onDragOver={(event) => {
            event.preventDefault();
            if (!running) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            if (!running) handleFile(event.dataTransfer.files?.[0]);
          }}
          className={`flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragging
              ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950/40"
              : "border-slate-300 hover:border-indigo-400 dark:border-slate-700"
          } ${running ? "pointer-events-none opacity-60" : ""}`}
        >
          <UploadCloud size={32} className="text-slate-400" />
          <p className="mt-3 text-sm font-medium">
            Drop a JSON file here, or <span className="text-indigo-600 dark:text-indigo-400">browse</span>
          </p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Up to {MAX_TICKETS} tickets. Each needs customer_name and ticket (ticket_id is optional).
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            disabled={running}
            onChange={(event) => handleFile(event.target.files?.[0])}
          />
        </label>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <button type="button" onClick={downloadSample} className={BUTTON_SECONDARY}>
            <Download size={16} /> Download sample file
          </button>
          {fileName && (
            <span className="inline-flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-400">
              <FileJson size={16} /> {fileName}
            </span>
          )}
        </div>

        {parseError && (
          <div
            role="alert"
            className="flex gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
          >
            <AlertCircle size={18} className="mt-0.5 shrink-0" />
            <p className="break-words">{parseError}</p>
          </div>
        )}
      </div>

      {rows.length > 0 && (
        <div className={`${CARD_CLASS} fade-in space-y-4`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">{rows.length} tickets ready</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {counts.done} done, {counts.failed} failed, {counts.skipped} skipped,{" "}
                {counts.pending} pending
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleReset}
                disabled={running}
                className={BUTTON_SECONDARY}
              >
                <RotateCcw size={16} /> Clear
              </button>
              {running ? (
                <button
                  type="button"
                  onClick={() => {
                    cancelRef.current = true;
                  }}
                  className={BUTTON_SECONDARY}
                >
                  <Square size={16} /> Stop after current
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleRun}
                  disabled={counts.pending === 0}
                  className={BUTTON_PRIMARY}
                >
                  <Play size={16} /> {startedBefore ? "Resume" : "Start processing"}
                </button>
              )}
            </div>
          </div>

          <div>
            <div className="mb-1 flex justify-between text-xs text-slate-500 dark:text-slate-400">
              <span>Progress</span>
              <span>{percent}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all"
                style={{ width: `${percent}%` }}
              />
            </div>
          </div>

          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {rows.map((row, index) => (
              <li key={`${row.ticket_id || "auto"}-${index}`} className="flex items-start gap-3 py-3">
                <span className="mt-0.5 w-6 shrink-0 text-xs text-slate-400">{index + 1}</span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">
                    {row.customer_name}
                    {row.ticket_id && (
                      <span className="ml-2 text-xs font-normal text-slate-500 dark:text-slate-400">
                        {row.ticket_id}
                      </span>
                    )}
                  </p>
                  <p className="truncate text-xs text-slate-500 dark:text-slate-400">{row.ticket}</p>
                  {row.message && (
                    <p className="mt-1 break-words text-xs text-red-600 dark:text-red-400">
                      {row.message}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-3 text-sm">
                  <StatusCell row={row} />
                  {row.record && (
                    <button
                      type="button"
                      onClick={() => setSelected(row.record)}
                      aria-label="View result"
                      className="rounded-md p-1.5 text-slate-500 transition hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                      <Eye size={16} />
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>

          {allFinished && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
              <p>
                Finished: {counts.done} processed, {counts.failed} failed, {counts.skipped} skipped.
              </p>
              <Link to="/dashboard" className="font-medium underline">
                Open dashboard
              </Link>
            </div>
          )}
        </div>
      )}

      <TicketModal ticket={selected} onClose={closeModal} />
    </div>
  );
}
