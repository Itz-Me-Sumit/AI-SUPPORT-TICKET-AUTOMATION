import { useEffect } from "react";
import { X } from "lucide-react";

import ResultCard from "./ResultCard";

export default function TicketModal({ ticket, onClose }) {
  // Close on Escape and lock page scrolling while the modal is open.
  useEffect(() => {
    if (!ticket) return undefined;

    const handleKey = (event) => {
      if (event.key === "Escape") onClose();
    };

    document.addEventListener("keydown", handleKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [ticket, onClose]);

  if (!ticket) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/60 p-4 backdrop-blur-sm"
    >
      <div className="my-8 w-full max-w-3xl" onClick={(event) => event.stopPropagation()}>
        <div className="mb-2 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow transition hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            <X size={16} /> Close
          </button>
        </div>
        <ResultCard ticket={ticket} />
      </div>
    </div>
  );
}
