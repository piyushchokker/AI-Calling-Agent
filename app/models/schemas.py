from datetime import datetime
from typing import Any

from pydantic import ConfigDict

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CompanyBase(BaseModel):
    name: str
    prompt_instructions: str | None = None
    assistant_id: str | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CustomerBase(BaseModel):
    company_id: str
    name: str
    phone: str
    status: str = "PENDING"


class CustomerCreate(CustomerBase):
    pass


class CustomerRead(CustomerBase):
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CampaignBase(BaseModel):
    company_id: str
    name: str
    objective: str | None = None


class CampaignCreate(CampaignBase):
    pass


class CampaignRead(CampaignBase):
    id: str


class WebhookEvent(BaseModel):
    event_type: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ApiMessage(BaseModel):
    message: str


class WebhookEventRead(BaseModel):
    id: str
    event_type: str
    payload: dict[str, Any]


class CallLogRead(BaseModel):
    id: str
    customer_id: str
    call_id: str | None = None
    transcript: str | None = None
    summary: str | None = None
    outcome: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class CampaignStartResponse(BaseModel):
    company_id: str
    processed_count: int
    errors: list[str] = Field(default_factory=list)


class TranscriptEvaluationResult(BaseModel):
    status: str
    reason: str
    confidence: float


class WebhookAckResponse(BaseModel):
    received: bool = True
    file_path: str
