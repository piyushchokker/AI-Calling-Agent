import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from app.config import settings
from app.dependencies import require_tenant_auth
from app.models.schemas import WebhookAckResponse
from app.services.repository import Repository
from app.graphs.evaluation_graph import run_evaluation_flow

router = APIRouter()
WEBHOOK_STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "webhooks"


def _extract_event_fields(payload: dict[str, Any]) -> tuple[str, str | None, str | None, str | None]:
    call_id = payload.get("call_id") or payload.get("callId") or payload.get("call", {}).get("id")
    transcript = payload.get("transcript") or payload.get("message", {}).get("transcript")
    summary = payload.get("summary") or payload.get("message", {}).get("summary")
    customer_id = payload.get("customer_id") or payload.get("metadata", {}).get("customer_id") or payload.get("customerId")
    return call_id, transcript, summary, customer_id


def _verify_webhook_signature(raw_body: bytes, signature: str | None) -> None:
    if not settings.vapi_webhook_secret:
        return
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature")

    import hmac
    import hashlib

    expected = hmac.new(settings.vapi_webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")


@router.post("/vapi", response_model=WebhookAckResponse, status_code=status.HTTP_200_OK)
async def handle_vapi_webhook(request: Request, background_tasks: BackgroundTasks, _: None = Depends(require_tenant_auth)) -> WebhookAckResponse:
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

    WEBHOOK_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    file_name = f"{timestamp}_{event_type.replace('.', '_').replace('/', '_')}.json"
    file_path = WEBHOOK_STORAGE_DIR / file_name

    file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if not customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="customer_id missing from webhook payload")

    background_tasks.add_task(_process_webhook, customer_id, call_id, transcript or "", summary or "", payload)

    return WebhookAckResponse(received=True, file_path=str(file_path))


async def _process_webhook(customer_id: str, call_id: str | None, transcript: str, summary: str, payload: dict[str, Any]) -> None:
    repository = Repository()
    await run_evaluation_flow(repository, customer_id, transcript, summary, call_id, payload)
