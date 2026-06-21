from typing import TypedDict


class DispatchGraphState(TypedDict, total=False):
    company_id: str
    pending_customers: list[dict]
    processed_count: int
    errors: list[str]


class EvaluationGraphState(TypedDict, total=False):
    customer_id: str
    transcript: str
    summary: str
    outcome: str
    confidence: float
    status: str
