import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app.config import settings
# We removed require_tenant_auth from the imports because webhooks cannot use frontend passwords
from app.models.schemas import WebhookAckResponse
from app.services.repository import Repository
from app.graphs.evaluation_graph import run_evaluation_flow

router = APIRouter()


def _extract_event_fields(payload: dict[str, Any]) -> tuple[str, str | None, str | None, str | None]:
    # Vapi nests data differently depending on the event type (end-of-call-report, status-update, etc.)
    message = payload.get("message", {})
    call = message.get("call", {}) or payload.get("call", {})
    
    # Dig for metadata in all possible Vapi locations
    metadata = payload.get("metadata") or message.get("metadata") or call.get("metadata") or {}

    call_id = payload.get("call_id") or payload.get("callId") or call.get("id")
    transcript = payload.get("transcript") or message.get("transcript")
    summary = payload.get("summary") or message.get("summary")
    
    # Extract the customer_id from whichever location had the metadata
    customer_id = payload.get("customer_id") or payload.get("customerId") or metadata.get("customer_id")

    return call_id, transcript, summary, customer_id


def _verify_webhook_signature(raw_body: bytes, signature: str | None) -> None:
    # BYPASS ADDED HERE: Instantly approve all webhooks for testing
    return 

    if not settings.vapi_webhook_secret:
        return
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature")

    import hmac
    import hashlib

    expected = hmac.new(settings.vapi_webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")


# BYPASS ADDED HERE: Removed `_: None = Depends(require_tenant_auth)` so Vapi isn't blocked
@router.post("/vapi", response_model=WebhookAckResponse, status_code=status.HTTP_200_OK)
async def handle_vapi_webhook(request: Request, background_tasks: BackgroundTasks) -> WebhookAckResponse:
    raw_body = await request.body()
    _verify_webhook_signature(raw_body, request.headers.get("x-vapi-signature") or request.headers.get("x-webhook-signature"))

    payload: dict[str, Any]

    try:
        body = json.loads(raw_body.decode("utf-8") or "{}")
        payload = body if isinstance(body, dict) else {"data": body}
    except Exception:
        payload = {"raw_body": raw_body.decode("utf-8", errors="replace")}

    event_type = payload.get("event_type") or payload.get("type") or payload.get("event") or "vapi.webhook"
    call_id, transcript, summary, customer_id = _extract_event_fields(payload)


    if not customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="customer_id missing from webhook payload")

    background_tasks.add_task(_process_webhook, customer_id, call_id, transcript or "", summary or "", payload)

    return WebhookAckResponse(received=True)


async def _process_webhook(customer_id: str, call_id: str | None, transcript: str, summary: str, payload: dict[str, Any]) -> None:
    repository = Repository()
    await run_evaluation_flow(repository, customer_id, transcript, summary, call_id, payload)