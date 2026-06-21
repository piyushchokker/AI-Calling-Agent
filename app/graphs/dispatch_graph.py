from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graphs.state import DispatchGraphState


def build_company_prompt(company: object, customer: object) -> str:
    company_name = getattr(company, "name", "")
    company_prompt = getattr(company, "prompt_instructions", "") or ""
    customer_name = getattr(customer, "name", "")
    return (
        f"You are calling on behalf of {company_name}. "
        f"Company instructions: {company_prompt}. "
        f"Speak with {customer_name} about qualifying them as a lead. "
        "Be concise, professional, and capture buying intent, timing, and budget."
    )


def _normalize_customer(customer: Any) -> dict[str, Any]:
    if isinstance(customer, dict):
        return customer
    return {
        "id": getattr(customer, "id", None),
        "company_id": getattr(customer, "company_id", None),
        "name": getattr(customer, "name", None),
        "phone": getattr(customer, "phone", None),
        "status": getattr(customer, "status", None),
    }


def create_dispatch_graph(repository, vapi_client):
    async def fetch_pending_customers(state: DispatchGraphState) -> dict[str, Any]:
        pending_customers = await repository.get_pending_customers(state["company_id"])
        return {"pending_customers": [_normalize_customer(customer) for customer in pending_customers], "errors": [], "processed_count": 0}

    async def trigger_calls(state: DispatchGraphState) -> dict[str, Any]:
        errors: list[str] = []
        processed_count = 0
        pending_customers = state.get("pending_customers", [])

        company = await repository.get_company(state["company_id"])
        if not company:
            return {"errors": [f"Company {state['company_id']} not found"], "processed_count": 0}

        for customer in pending_customers:
            try:
                dynamic_prompt = build_company_prompt(company, customer)
                await vapi_client.create_outbound_call(customer, company, dynamic_prompt)
                await repository.update_customer_status(customer["id"], "CALL_INITIATED")
                processed_count += 1
            except Exception as exc:
                errors.append(str(exc))

        return {"errors": errors, "processed_count": processed_count}

    async def mark_call_initiated(state: DispatchGraphState) -> dict[str, Any]:
        return summarize_campaign(state)

    graph = StateGraph(DispatchGraphState)
    graph.add_node("fetch_pending_customers", fetch_pending_customers)
    graph.add_node("trigger_calls", trigger_calls)
    graph.add_node("mark_call_initiated", mark_call_initiated)
    graph.add_edge(START, "fetch_pending_customers")
    graph.add_edge("fetch_pending_customers", "trigger_calls")
    graph.add_edge("trigger_calls", "mark_call_initiated")
    graph.add_edge("mark_call_initiated", END)
    return graph.compile()


async def run_dispatch_campaign(repository, vapi_client, company_id: str) -> dict[str, Any]:
    graph = create_dispatch_graph(repository, vapi_client)
    return await graph.ainvoke({"company_id": company_id, "pending_customers": [], "processed_count": 0, "errors": []})


def summarize_campaign(state: DispatchGraphState) -> dict[str, object]:
    return {
        "company_id": state["company_id"],
        "processed_count": state.get("processed_count", 0),
        "errors": state.get("errors", []),
    }
