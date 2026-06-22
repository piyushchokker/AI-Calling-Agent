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


def _extract_event_fields(payload: dict[str, Any]) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    # Base message and call objects
    message = payload.get("message", {})
    call = message.get("call", {}) or payload.get("call", {})
    
    # Vapi nests summary and transcript in these specific objects
    artifact = message.get("artifact", {})
    analysis = message.get("analysis", {})
    
    # Dig for metadata
    metadata = payload.get("metadata") or message.get("metadata") or call.get("metadata") or {}

    # Extract fields using aggressive fallback logic
    call_id = payload.get("call_id") or payload.get("callId") or call.get("id")
    customer_id = payload.get("customer_id") or payload.get("customerId") or metadata.get("customer_id")
    
    # Check the top level (Postman), then message, then artifact/analysis (Real Vapi)
    transcript = payload.get("transcript") or message.get("transcript") or artifact.get("transcript")
    summary = payload.get("summary") or message.get("summary") or analysis.get("summary")
    ended_reason = message.get("endedReason") or call.get("endedReason")

    return call_id, transcript, summary, customer_id, ended_reason


def _verify_webhook_signature(request: Request) -> None:
    if not settings.vapi_webhook_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook secret is not configured on the server")
        
    # Vapi's new dashboard requires passing the secret as a custom header.
    # We will check the 'x-vapi-secret' header against our .env secret.
    incoming_secret = request.headers.get("x-vapi-secret")
    
    if not incoming_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing x-vapi-secret header")
        
    if incoming_secret != settings.vapi_webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")


# BYPASS ADDED HERE: Removed `_: None = Depends(require_tenant_auth)` so Vapi isn't blocked
@router.post("/vapi", response_model=WebhookAckResponse, status_code=status.HTTP_200_OK)
async def handle_vapi_webhook(request: Request, background_tasks: BackgroundTasks) -> WebhookAckResponse:
    _verify_webhook_signature(request)
    raw_body = await request.body()

    payload: dict[str, Any]

    try:
        body = json.loads(raw_body.decode("utf-8") or "{}")
        payload = body if isinstance(body, dict) else {"data": body}
    except Exception:
        payload = {"raw_body": raw_body.decode("utf-8", errors="replace")}

    event_type = payload.get("event_type") or payload.get("type") or payload.get("event") or "vapi.webhook"
    call_id, transcript, summary, customer_id, ended_reason = _extract_event_fields(payload)


    if not customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="customer_id missing from webhook payload")

    background_tasks.add_task(_process_webhook, customer_id, call_id, transcript or "", summary or "", payload, ended_reason)

    return WebhookAckResponse(received=True)


async def _process_webhook(customer_id: str, call_id: str | None, transcript: str, summary: str, payload: dict[str, Any], ended_reason: str | None) -> None:
    repository = Repository()
    await run_evaluation_flow(repository, customer_id, transcript, summary, call_id, payload, ended_reason)