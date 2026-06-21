import pytest

from app.graphs.dispatch_graph import run_dispatch_campaign
from app.graphs.evaluation_graph import run_evaluation_flow


class DummyRepo:
    async def get_pending_customers(self, company_id, limit=100, offset=0):
        return [{"id": "cust_1", "company_id": company_id, "name": "John Smith", "phone": "+10000000001", "status": "PENDING"}]

    async def get_company(self, company_id):
        return {"id": company_id, "name": "Dream Homes Realty", "prompt_instructions": "Qualify home buyers"}

    async def update_customer_status(self, customer_id, status):
        return {"id": customer_id, "status": status}

    async def create_call_log(self, payload):
        return payload


class DummyVapi:
    async def create_outbound_call(self, customer, company, dynamic_prompt):
        return "call_123"


@pytest.mark.asyncio
async def test_dispatch_graph_runs_campaign():
    result = await run_dispatch_campaign(DummyRepo(), DummyVapi(), "cmp_1")
    assert result["processed_count"] == 1
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_evaluation_graph_runs_flow(monkeypatch):
    from app.graphs import evaluation_graph

    async def fake_evaluate_transcript(transcript):
        return {"status": "QUALIFIED", "reason": "positive", "confidence": 0.9}

    monkeypatch.setattr(evaluation_graph, "evaluate_transcript", fake_evaluate_transcript)
    result = await run_evaluation_flow(DummyRepo(), "cust_1", "great call", "summary", "call_123", {"foo": "bar"})
    assert result["status"] == "QUALIFIED"
