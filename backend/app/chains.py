
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from langchain_core.output_parsers import StrOutputParser

from langchain_core.runnables import RunnableBranch

from langchain_core.runnables import Runnable

from app.schemas import (
    AccountAnalysis,
    BillingAnalysis,
    CancellationRefundAnalysis,
    GeneralAnalysis,
    OrderDeliveryAnalysis,
    ResolutionDecision,
    TechnicalAnalysis,
    TicketTriage,
)


# Project root so prompt paths work from any file location.
PROJECT_ROOT = Path(__file__).resolve().parents[1]



# Short focus text passed into the shared case_analysis prompt.
ANALYSIS_FOCUS = {
    "billing": (
        "- issue\n"
        "- amount\n"
        "- transaction_count\n"
        "- refund_required"
    ),
    "technical": (
        "- issue\n"
        "- affected_feature\n"
        "- error_message\n"
        "- troubleshooting_required"
    ),
    "account": (
        "- issue\n"
        "- access_problem\n"
        "- verification_required\n"
        "- account_status"
    ),
    "cancellation_refund": (
        "- request_type\n"
        "- reason\n"
        "- refund_required\n"
        "- retention_opportunity"
    ),
    "order_delivery": (
        "- issue\n"
        "- order_status\n"
        "- delivery_problem\n"
        "- customer_request"
    ),
    "general": (
        "- issue\n"
        "- customer_request\n"
        "- additional_context"
    ),
}


def load_prompt(file_path) -> str:
    """Read a prompt file and return its text."""

    path = Path(file_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found here: {path}")


def create_triage_chain(llm) -> Runnable:
    """Create the chain that classifies a ticket using structured output."""

    prompt_text = load_prompt("prompts/classification_prompt.txt")

    prompt = ChatPromptTemplate.from_template(
        prompt_text
    )

    # Convert the LLM response directly into the TicketTriage schema.
    structured_llm = llm.with_structured_output(TicketTriage)

    chain = prompt | structured_llm

    return chain


def _create_analysis_chain(llm, category, schema) -> Runnable:
    """Create a category-specific analysis chain."""

    prompt_text = load_prompt("prompts/case_analysis_prompt.txt")

    prompt = ChatPromptTemplate.from_template(prompt_text)

    # Fill the common prompt with category-specific instructions.
    prompt = prompt.partial(
        category=category,
        analysis_focus=ANALYSIS_FOCUS[category]
    )

    structured_llm = llm.with_structured_output(schema)

    chain = prompt | structured_llm

    return chain


def create_billing_chain(llm) -> Runnable:
    """Create the billing analysis chain."""

    return _create_analysis_chain(
        llm,
        "billing",
        BillingAnalysis
    )


def create_technical_chain(llm) -> Runnable:
    """Create the technical issue analysis chain."""

    return _create_analysis_chain(
        llm,
        "technical",
        TechnicalAnalysis
    )


def create_account_chain(llm) -> Runnable:
    """Create the account issue analysis chain."""

    return _create_analysis_chain(
        llm,
        "account",
        AccountAnalysis
    )


def create_cancellation_refund_chain(llm) -> Runnable:
    """Create the cancellation/refund analysis chain."""

    return _create_analysis_chain(
        llm,
        "cancellation_refund",
        CancellationRefundAnalysis
    )


def create_order_delivery_chain(llm) -> Runnable:
    """Create the order and delivery analysis chain."""

    return _create_analysis_chain(
        llm,
        "order_delivery",
        OrderDeliveryAnalysis
    )


def create_general_chain(llm) -> Runnable:
    """Create the fallback analysis chain for general tickets."""

    return _create_analysis_chain(
        llm,
        "general",
        GeneralAnalysis
    )


def create_router(llm) -> Runnable:
    """Route each ticket to the analysis chain matching its category."""

    billing_chain = create_billing_chain(llm)

    technical_chain = create_technical_chain(llm)

    account_chain = create_account_chain(llm)

    cancellation_refund_chain = create_cancellation_refund_chain(llm)

    order_delivery_chain = create_order_delivery_chain(llm)

    general_chain = create_general_chain(llm)

    return RunnableBranch(
        (lambda x: x["category"] == "billing", billing_chain),
        (lambda x: x["category"] == "technical", technical_chain),
        (lambda x: x["category"] == "account", account_chain),
        (
            lambda x: x["category"] == "cancellation_refund",
            cancellation_refund_chain
        ),
        (
            lambda x: x["category"] == "order_delivery",
            order_delivery_chain
        ),
        general_chain,
    )


def create_resolution_chain(llm) -> Runnable:
    """Create the chain that decides how the ticket should be resolved."""

    prompt_text = load_prompt("prompts/resolution_prompt.txt")

    prompt = ChatPromptTemplate.from_template(prompt_text)

    structured_llm = llm.with_structured_output(ResolutionDecision)

    chain = prompt | structured_llm

    return chain


def create_response_chain(llm) -> Runnable:
    """Create the final chain that generates the customer response."""

    prompt_text = load_prompt("prompts/response_prompt.txt")

    prompt = ChatPromptTemplate.from_template(
        prompt_text
    )

    # Parse the final LLM response into a plain string.
    return prompt | llm | StrOutputParser()