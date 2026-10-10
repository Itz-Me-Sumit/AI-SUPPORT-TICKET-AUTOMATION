from typing import Literal, Annotated, Optional

from pydantic import BaseModel, Field


# **Allowed values used across triage and resolution stages**

Category = Literal[
    "billing",
    "technical",
    "account",
    "cancellation_refund",
    "order_delivery",
    "general"
]

Priority = Literal[
    "low",
    "medium",
    "high",
    "critical"
]

ResolutionType = Literal[
    "self_service",
    "resolve",
    "escalate",
    "request_information"
]


class TicketTriage(BaseModel):

    """Represents the initial classification of a support ticket."""

    category: Annotated[
        Optional[Category],
        Field(description="support ticket category")
    ]

    priority: Annotated[
        Optional[Priority],
        Field(description="urgency of the ticket")
    ]

    language: Annotated[
        Optional[str],
        Field(description="language used in the customer ticket")
    ]


class BillingAnalysis(BaseModel):

    """Represents the extracted details of a billing-related issue."""

    issue: Annotated[
        Optional[str],
        Field(description="short summary of billing problem")
    ]

    amount: Annotated[
        Optional[str],
        Field(description="money amount mentioned, or 'unknown'")
    ]

    transaction_count: Annotated[
        Optional[int],
        Field(description="number of charges mentioned")
    ]

    refund_required: Annotated[
        Optional[bool],
        Field(description="whether a refund appears needed")
    ]


class TechnicalAnalysis(BaseModel):

    """Represents the extracted details of a technical support issue."""

    issue: Annotated[
        Optional[str],
        Field(description="short summary of the technical problem")
    ]

    affected_feature: Annotated[
        Optional[str],
        Field(description="feature or area that is broken")
    ]

    error_message: Annotated[
        Optional[str],
        Field(description="error text if mentioned, else 'none'")
    ]

    troubleshooting_required: Annotated[
        Optional[bool],
        Field(description="whether troubleshooting is still needed")
    ]


class AccountAnalysis(BaseModel):

    """Represents the extracted details of an account-related issue."""

    issue: Annotated[
        Optional[str],
        Field(description="short summary of the account problem")
    ]

    access_problem: Annotated[
        Optional[bool],
        Field(description="whether login or access is blocked")
    ]

    verification_required: Annotated[
        Optional[bool],
        Field(description="whether identity verification is needed")
    ]

    account_status: Annotated[
        Optional[Literal["active", "locked", "unknown"]],
        Field(
            description="likely account status, for example - 'active', 'locked', 'unknown'"
        )
    ]


class CancellationRefundAnalysis(BaseModel):

    """Represents the extracted details of a cancellation or refund request."""

    request_type: Annotated[
        Optional[str],
        Field(
            description="what the customer wants, for example - 'cancel', 'refund', or 'both'"
        )
    ]

    reason: Annotated[
        Optional[str],
        Field(description="reason given by customer")
    ]

    refund_required: Annotated[
        Optional[bool],
        Field(description="whether a refund is needed or requested")
    ]

    retention_opportunity: Annotated[
        Optional[bool],
        Field(description="whether there may be a chance to retain the customer")
    ]


class OrderDeliveryAnalysis(BaseModel):

    """Represents the extracted details of an order or delivery-related issue."""

    issue: Annotated[
        Optional[str],
        Field(description="short summary of order or delivery problem")
    ]

    order_status: Annotated[
        Optional[str],
        Field(description="current status if mentioned, otherwise 'unknown'")
    ]

    delivery_problem: Annotated[
        Optional[bool],
        Field(description="whether delivery is the main problem")
    ]

    customer_request: Annotated[
        Optional[str],
        Field(description="what the customer wants to be done")
    ]


class GeneralAnalysis(BaseModel):

    """Represents the extracted details of a general customer request."""

    issue: Annotated[
        Optional[str],
        Field(description="short summary of customer request")
    ]

    customer_request: Annotated[
        Optional[str],
        Field(description="what the customer is asking for")
    ]

    additional_context: Annotated[
        Optional[str],
        Field(description="any extra useful context from the ticket")
    ]


class ResolutionDecision(BaseModel):

    """Represents the recommended resolution and next action for a support ticket."""

    resolution_type: Annotated[
        Optional[ResolutionType],
        Field(description="type of resolution selected for the support ticket")
    ]

    recommended_action: Annotated[
        Optional[str],
        Field(description="specific action recommended as the next step")
    ]

    requires_human: Annotated[
        Optional[bool],
        Field(description="whether human assistance is required to handle the ticket")
    ]

    reason: Annotated[
        Optional[str],
        Field(description="reason for selecting the recommended resolution")
    ]


class TicketResult(BaseModel):

    """Represents the final structured result generated after processing a support ticket."""

    ticket_id: Optional[str]
    customer_name: Optional[str]
    category: Optional[str]
    priority: Optional[str]
    language: Optional[str]
    case_summary: Optional[str]
    resolution_type: Optional[str]
    recommended_action: Optional[str]
    requires_human: Optional[bool]
    resolution_reason: Optional[str]
    response: Optional[str]