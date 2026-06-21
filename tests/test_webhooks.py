import pytest

@pytest.mark.asyncio
async def test_webhook_accepts_payload(client, monkeypatch):
    from app.routes import webhooks

    async def fake_run_evaluation_flow(repository, customer_id, transcript, summary, call_id, metadata):
        return {"status": "QUALIFIED"}

    monkeypatch.setattr(webhooks, "run_evaluation_flow", fake_run_evaluation_flow)

    payload = {
        "event_type": "call.completed",
        "customer_id": "cust_1",
        "call_id": "call_123",
        "transcript": "hello",
        "summary": "summary",
    }

    response = client.post("/api/v1/webhooks/vapi", json=payload)
    assert response.status_code == 200
    assert response.json()["received"] is True