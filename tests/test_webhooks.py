import pytest


@pytest.mark.asyncio
async def test_webhook_saves_file_and_accepts_payload(client, monkeypatch, tmp_path):
    from app.routes import webhooks

    monkeypatch.setattr(webhooks, "WEBHOOK_STORAGE_DIR", tmp_path)

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
    assert list(tmp_path.glob("*.json"))
