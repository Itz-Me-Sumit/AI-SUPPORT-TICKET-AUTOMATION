import logging
import time

from app.chains import (
    create_resolution_chain,
    create_response_chain,
    create_router,
    create_triage_chain,
)

logger = logging.getLogger(__name__)

# Friendly labels used for logging
CHAIN_LABELS = {
    "billing": "Billing Chain",
    "technical": "Technical Chain",
    "account": "Account Chain",
    "cancellation_refund": "Cancellation/Refund Chain",
    "order_delivery": "Order/Delivery Chain",
    "general": "General Chain",
}


def build_workflow(llm) -> dict:
    """Create all chains once and return them in a dictionary."""
    return {
        "triage_chain": create_triage_chain(llm),
        "router": create_router(llm),
        "resolution_chain": create_resolution_chain(llm),
        "response_chain": create_response_chain(llm),
    }


def _require(value, stage: str):
    """Raise a clear error if the LLM returned nothing for a stage.

    Some free models return None for structured output when they
    do not support tool calling properly.
    """
    if value is None:
        raise ValueError(
            f"The model returned an empty result during the '{stage}' stage. "
            "Try again or switch to a model that supports structured output."
        )
    return value


async def process_ticket(ticket: dict, workflow: dict) -> dict:
    """Run the full pipeline for one ticket and return a plain dictionary.

    Stages:
        1. Triage (category, priority, language)
        2. Category-specific case analysis
        3. Resolution decision
        4. Customer response generation
    """
    started = time.perf_counter()

    customer_name = ticket["customer_name"]
    ticket_text = ticket["ticket"]

    # Stage 1: triage
    triage = _require(
        await workflow["triage_chain"].ainvoke(
            {"customer_name": customer_name, "ticket": ticket_text}
        ),
        "triage",
    )

    # Fall back to safe defaults if the model left a field empty
    category = triage.category or "general"
    priority = triage.priority or "medium"
    language = triage.language or "English"

    logger.info(
        "Ticket %s -> category=%s priority=%s route=%s",
        ticket.get("ticket_id"),
        category,
        priority,
        CHAIN_LABELS.get(category, "General Chain"),
    )

    # Stage 2: routed case analysis
    case_analysis = _require(
        await workflow["router"].ainvoke(
            {
                "category": category,
                "customer_name": customer_name,
                "ticket": ticket_text,
            }
        ),
        "case analysis",
    )
    case_analysis_dict = case_analysis.model_dump()
    case_analysis_text = case_analysis.model_dump_json(indent=2)

    # Stage 3: resolution decision
    resolution = _require(
        await workflow["resolution_chain"].ainvoke(
            {
                "customer_name": customer_name,
                "ticket": ticket_text,
                "category": category,
                "priority": priority,
                "language": language,
                "case_analysis": case_analysis_text,
            }
        ),
        "resolution",
    )

    # Critical tickets always need a human, whatever the model says
    requires_human = bool(resolution.requires_human)
    if priority == "critical":
        requires_human = True

    # Stage 4: customer response
    response_text = await workflow["response_chain"].ainvoke(
        {
            "customer_name": customer_name,
            "ticket": ticket_text,
            "category": category,
            "priority": priority,
            "language": language,
            "case_analysis": case_analysis_text,
            "resolution_type": resolution.resolution_type,
            "recommended_action": resolution.recommended_action,
            "requires_human": requires_human,
            "resolution_reason": resolution.reason,
        }
    )

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return {
        "category": category,
        "priority": priority,
        "language": language,
        "case_analysis": case_analysis_dict,
        "resolution_type": resolution.resolution_type,
        "recommended_action": resolution.recommended_action,
        "requires_human": requires_human,
        "resolution_reason": resolution.reason,
        "response": (response_text or "").strip(),
        "processing_ms": elapsed_ms,
    }
