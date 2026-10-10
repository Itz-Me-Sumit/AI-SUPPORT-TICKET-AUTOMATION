// Shared style strings so every page looks consistent.
export const CARD_CLASS =
  "rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900";

export const INPUT_CLASS =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 " +
  "focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 " +
  "dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder-slate-500";

export const BUTTON_PRIMARY =
  "inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white " +
  "transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50";

export const BUTTON_SECONDARY =
  "inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium " +
  "text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 " +
  "dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800";

export const CATEGORY_STYLES = {
  billing: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  technical: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  account: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
  cancellation_refund: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  order_delivery: "bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300",
  general: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

export const PRIORITY_STYLES = {
  low: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300",
  high: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300",
  critical: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
};

export const RESOLUTION_STYLES = {
  self_service: "bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300",
  resolve: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300",
  escalate: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
  request_information: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300",
};

// "order_delivery" -> "Order Delivery"
export function humanize(value) {
  if (!value) return "—";
  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

// The backend sends UTC timestamps without a timezone suffix, so add "Z" when missing.
export function formatDate(value) {
  if (!value) return "—";
  const iso = /(Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`;
  return new Date(iso).toLocaleString();
}

export const SAMPLE_TICKETS = [
  {
    label: "Double charge",
    customer_name: "Rahul Sharma",
    ticket:
      "I was charged twice for my Premium subscription this month. The amount is $29.99 each time. Please refund one of the duplicate charges.",
  },
  {
    label: "App crash",
    customer_name: "Priya Nair",
    ticket:
      "The mobile app crashes every time I open the Settings page. I see an error message that says 'Unexpected null pointer'. I have already tried reinstalling the app.",
  },
  {
    label: "Cannot log in",
    customer_name: "Amit Verma",
    ticket:
      "I cannot log into my account. My email is amit.verma@email.com and I keep getting 'Invalid credentials' even after resetting my password twice.",
  },
  {
    label: "Cancel + refund",
    customer_name: "Sneha Patel",
    ticket:
      "I want to cancel my annual plan and request a refund for the unused months. I am switching to a competitor because your pricing went up.",
  },
  {
    label: "Late delivery",
    customer_name: "John Miller",
    ticket:
      "My order #ORD-78421 was supposed to arrive yesterday but the tracking still says 'In transit'. Can you check the delivery status and tell me when it will arrive?",
  },
  {
    label: "Production outage",
    customer_name: "Carlos Rivera",
    ticket:
      "URGENT: My entire production dashboard is down and showing HTTP 503. Customers cannot place orders. This started 20 minutes ago after your latest update.",
  },
];
