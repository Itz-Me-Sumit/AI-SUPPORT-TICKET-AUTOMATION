import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  Bot,
  ChevronLeft,
  ChevronRight,
  Clock,
  Inbox,
  Loader2,
  RefreshCw,
  Search,
  Ticket,
  Trash2,
  UserCheck,
  XCircle,
} from "lucide-react";

import Badge from "../components/Badge";
import TicketModal from "../components/TicketModal";
import { deleteTicket, getStats, listTickets } from "../lib/api";
import {
  BUTTON_PRIMARY,
  BUTTON_SECONDARY,
  CARD_CLASS,
  CATEGORY_STYLES,
  INPUT_CLASS,
  PRIORITY_STYLES,
  RESOLUTION_STYLES,
  formatDate,
  humanize,
} from "../lib/constants";

const PAGE_SIZE = 10;
const CATEGORIES = [
  "billing",
  "technical",
  "account",
  "cancellation_refund",
  "order_delivery",
  "general",
];
const PRIORITIES = ["low", "medium", "high", "critical"];

function StatCard({ label, value, hint, icon: Icon, tone }) {
  return (
    <div className={CARD_CLASS}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {label}
        </p>
        <span className={`rounded-lg p-2 ${tone}`}>
          <Icon size={16} />
        </span>
      </div>
      <p className="mt-3 text-2xl font-bold">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
    </div>
  );
}

function Breakdown({ title, data }) {
  const entries = Object.entries(data || {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(([, count]) => count), 1);

  return (
    <div className={CARD_CLASS}>
      <h3 className="mb-3 text-sm font-semibold">{title}</h3>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No data yet.</p>
      ) : (
        <ul className="space-y-2.5">
          {entries.map(([key, count]) => (
            <li key={key}>
              <div className="mb-1 flex justify-between text-xs">
                <span>{humanize(key)}</span>
                <span className="font-medium">{count}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                <div
                  className="h-full rounded-full bg-indigo-500 transition-all"
                  style={{ width: `${(count / max) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function HistoryPage() {
  const [stats, setStats] = useState(null);
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const [selected, setSelected] = useState(null);
  const [deletingId, setDeletingId] = useState("");

  // Ignore responses that belong to an older request.
  const requestId = useRef(0);

  // Debounce the search box so we do not call the API on every keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const load = useCallback(async () => {
    const id = ++requestId.current;
    setLoading(true);
    setError("");

    try {
      const [list, statData] = await Promise.all([
        listTickets({ search, category, priority, status, page, page_size: PAGE_SIZE }),
        getStats(),
      ]);

      if (id !== requestId.current) return;

      // If the last item of the last page was deleted, go back one page.
      if (list.items.length === 0 && page > 1) {
        setPage(page - 1);
        return;
      }

      setData(list);
      setStats(statData);
    } catch (err) {
      if (id === requestId.current) setError(err.message);
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [search, category, priority, status, page]);

  useEffect(() => {
    load();
  }, [load]);

  const closeModal = useCallback(() => setSelected(null), []);

  async function handleDelete(ticket) {
    const confirmed = window.confirm(
      `Delete ticket ${ticket.ticket_id}? This cannot be undone.`
    );
    if (!confirmed) return;

    setDeletingId(ticket.ticket_id);
    try {
      await deleteTicket(ticket.ticket_id);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingId("");
    }
  }

  function changeFilter(setter) {
    return (event) => {
      setter(event.target.value);
      setPage(1);
    };
  }

  const hasFilters = Boolean(search || category || priority || status);
  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  const firstLoad = loading && !stats;
  const noTicketsAtAll = stats && stats.total === 0 && !hasFilters;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Overview of every processed ticket.
          </p>
        </div>
        <button type="button" onClick={load} disabled={loading} className={BUTTON_SECONDARY}>
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> Refresh
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="flex gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          <AlertCircle size={18} className="mt-0.5 shrink-0" />
          <p className="break-words">{error}</p>
        </div>
      )}

      {firstLoad && (
        <div className="flex items-center justify-center gap-2 py-20 text-sm text-slate-500">
          <Loader2 size={18} className="animate-spin" /> Loading dashboard...
        </div>
      )}

      {noTicketsAtAll && (
        <div className={`${CARD_CLASS} flex flex-col items-center py-14 text-center`}>
          <Inbox size={36} className="text-slate-400" />
          <h2 className="mt-3 text-lg font-semibold">No tickets yet</h2>
          <p className="mt-1 max-w-sm text-sm text-slate-600 dark:text-slate-400">
            Process your first ticket and its analysis will show up here.
          </p>
          <Link to="/" className={`${BUTTON_PRIMARY} mt-5`}>
            Submit a ticket
          </Link>
        </div>
      )}

      {stats && !noTicketsAtAll && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard
              label="Total tickets"
              value={stats.total}
              hint={`${stats.completed} completed`}
              icon={Ticket}
              tone="bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
            />
            <StatCard
              label="Human required"
              value={`${stats.human_required_pct}%`}
              hint={`${stats.human_required} tickets`}
              icon={UserCheck}
              tone="bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
            />
            <StatCard
              label="Critical"
              value={stats.critical}
              hint="Highest priority"
              icon={AlertTriangle}
              tone="bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
            />
            <StatCard
              label="Avg. time"
              value={`${(stats.avg_processing_ms / 1000).toFixed(1)}s`}
              hint="Per completed ticket"
              icon={Clock}
              tone="bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
            />
            <StatCard
              label="Failed"
              value={stats.failed}
              hint="Processing errors"
              icon={XCircle}
              tone="bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
            />
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <Breakdown title="By category" data={stats.by_category} />
            <Breakdown title="By priority" data={stats.by_priority} />
            <Breakdown title="By resolution" data={stats.by_resolution} />
          </div>

          <div className={`${CARD_CLASS} space-y-4`}>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="relative md:col-span-1">
                <Search
                  size={16}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="Search tickets..."
                  className={`${INPUT_CLASS} pl-9`}
                />
              </div>

              <select value={category} onChange={changeFilter(setCategory)} className={INPUT_CLASS}>
                <option value="">All categories</option>
                {CATEGORIES.map((item) => (
                  <option key={item} value={item}>
                    {humanize(item)}
                  </option>
                ))}
              </select>

              <select value={priority} onChange={changeFilter(setPriority)} className={INPUT_CLASS}>
                <option value="">All priorities</option>
                {PRIORITIES.map((item) => (
                  <option key={item} value={item}>
                    {humanize(item)}
                  </option>
                ))}
              </select>

              <select value={status} onChange={changeFilter(setStatus)} className={INPUT_CLASS}>
                <option value="">All statuses</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            {data.items.length === 0 ? (
              <p className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">
                {loading ? "Loading..." : "No tickets match your filters."}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                      <th className="px-3 py-2 font-medium">Ticket</th>
                      <th className="px-3 py-2 font-medium">Customer</th>
                      <th className="px-3 py-2 font-medium">Category</th>
                      <th className="px-3 py-2 font-medium">Priority</th>
                      <th className="px-3 py-2 font-medium">Resolution</th>
                      <th className="px-3 py-2 font-medium">Handler</th>
                      <th className="px-3 py-2 font-medium">Created</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((ticket) => {
                      const failed = ticket.status === "failed";
                      return (
                        <tr
                          key={ticket.ticket_id}
                          onClick={() => setSelected(ticket)}
                          className="cursor-pointer border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40"
                        >
                          <td className="px-3 py-3">
                            <p className="font-medium">{ticket.ticket_id}</p>
                            <p className="max-w-[16rem] truncate text-xs text-slate-500 dark:text-slate-400">
                              {ticket.ticket_text}
                            </p>
                          </td>
                          <td className="px-3 py-3">{ticket.customer_name}</td>
                          <td className="px-3 py-3">
                            {failed ? (
                              <Badge className="bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">
                                Failed
                              </Badge>
                            ) : (
                              <Badge
                                className={CATEGORY_STYLES[ticket.category] || CATEGORY_STYLES.general}
                              >
                                {humanize(ticket.category)}
                              </Badge>
                            )}
                          </td>
                          <td className="px-3 py-3">
                            {ticket.priority ? (
                              <Badge className={PRIORITY_STYLES[ticket.priority] || PRIORITY_STYLES.low}>
                                {humanize(ticket.priority)}
                              </Badge>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="px-3 py-3">
                            {ticket.resolution_type ? (
                              <Badge
                                className={
                                  RESOLUTION_STYLES[ticket.resolution_type] || RESOLUTION_STYLES.resolve
                                }
                              >
                                {humanize(ticket.resolution_type)}
                              </Badge>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="px-3 py-3">
                            {failed ? (
                              "—"
                            ) : ticket.requires_human ? (
                              <span className="inline-flex items-center gap-1 text-amber-700 dark:text-amber-400">
                                <UserCheck size={14} /> Human
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-emerald-700 dark:text-emerald-400">
                                <Bot size={14} /> Auto
                              </span>
                            )}
                          </td>
                          <td className="whitespace-nowrap px-3 py-3 text-xs text-slate-500 dark:text-slate-400">
                            {formatDate(ticket.created_at)}
                          </td>
                          <td className="px-3 py-3 text-right">
                            <button
                              type="button"
                              aria-label={`Delete ${ticket.ticket_id}`}
                              disabled={deletingId === ticket.ticket_id}
                              onClick={(event) => {
                                event.stopPropagation();
                                handleDelete(ticket);
                              }}
                              className="rounded-md p-1.5 text-slate-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50 dark:hover:bg-red-950"
                            >
                              {deletingId === ticket.ticket_id ? (
                                <Loader2 size={16} className="animate-spin" />
                              ) : (
                                <Trash2 size={16} />
                              )}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
              <p className="text-slate-500 dark:text-slate-400">
                {data.total} ticket{data.total === 1 ? "" : "s"} found
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  disabled={page <= 1 || loading}
                  className={BUTTON_SECONDARY}
                >
                  <ChevronLeft size={16} /> Prev
                </button>
                <span className="px-2 text-slate-600 dark:text-slate-400">
                  Page {page} of {totalPages}
                </span>
                <button
                  type="button"
                  onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                  disabled={page >= totalPages || loading}
                  className={BUTTON_SECONDARY}
                >
                  Next <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      <TicketModal ticket={selected} onClose={closeModal} />
    </div>
  );
}
