// Empty base URL means "same origin" (Vite proxy in dev, nginx in production).
const BASE = import.meta.env.VITE_API_URL || "";

function formatError(data, status) {
  const detail = data && data.detail;

  if (typeof detail === "string") return detail;

  // FastAPI validation errors come as a list of objects
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : "field";
        return `${field}: ${item.msg}`;
      })
      .join(" | ");
  }

  return `Request failed (status ${status}).`;
}

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("Cannot reach the server. Please check that the backend is running.");
  }

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(formatError(data, response.status));
  }

  return data;
}

export function createTicket(payload) {
  return request("/api/tickets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createBatch(tickets) {
  return request("/api/tickets/batch", {
    method: "POST",
    body: JSON.stringify({ tickets }),
  });
}

export function listTickets(params = {}) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  });

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request(`/api/tickets${suffix}`);
}

export function getTicket(ticketId) {
  return request(`/api/tickets/${encodeURIComponent(ticketId)}`);
}

export function deleteTicket(ticketId) {
  return request(`/api/tickets/${encodeURIComponent(ticketId)}`, { method: "DELETE" });
}

export function getStats() {
  return request("/api/stats");
}
