// Helpers for tickets created from phone calls (their ID starts with CALL-).

export function isVoiceTicket(ticket) {
  return Boolean(ticket && String(ticket.ticket_id || "").startsWith("CALL-"));
}

// Turns "assistant: hi\nuser: hello" into [{ speaker, text }]
export function parseTranscript(text) {
  const turns = [];

  for (const raw of String(text || "").split("\n")) {
    const line = raw.trim();
    if (!line || line.startsWith("Phone call transcript")) continue;

    const match = line.match(/^(assistant|user)\s*:\s*(.*)$/i);
    if (match) {
      turns.push({ speaker: match[1].toLowerCase(), text: match[2].trim() });
    } else if (turns.length > 0) {
      turns[turns.length - 1].text += " " + line;
    }
  }

  return turns;
}

// Short text for the dashboard table.
export function ticketPreview(ticket) {
  if (!isVoiceTicket(ticket)) return ticket.ticket_text;

  const firstCustomerLine = parseTranscript(ticket.ticket_text).find(
    (turn) => turn.speaker === "user"
  );
  return firstCustomerLine ? firstCustomerLine.text : "Voice call";
}
