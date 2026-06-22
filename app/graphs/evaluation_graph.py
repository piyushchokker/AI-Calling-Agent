import json
from typing import Any

# pyrefly: ignore [missing-import]
from langgraph.graph import END, START, StateGraph
# pyrefly: ignore [missing-import]
from openai import AsyncOpenAI

from app.config import settings
from app.graphs.state import EvaluationGraphState

def create_evaluation_graph(repository):
    
    # 1. EVALUATE TRANSCRIPT FIRST
    async def evaluate_call(state: EvaluationGraphState) -> dict[str, Any]:
        result = await evaluate_transcript(state.get("transcript", ""))
        return {"status": result["status"], "confidence": result["confidence"], "reason": result["reason"]}

    # 2. CHECK CONFIDENCE RULE
    async def determine_status(state: EvaluationGraphState) -> dict[str, Any]:
        result = apply_low_confidence_rule({
            "status": state.get("status", "NEEDS_REVIEW"),
            "confidence": state.get("confidence", 0.0),
            "reason": state.get("reason", "")
        })
        return {"status": result["status"], "confidence": result["confidence"], "reason": result.get("reason", "")}

    # 3. STORE IN DATABASE NOW THAT WE HAVE THE ACTUAL STATUS
    async def store_transcript(state: EvaluationGraphState) -> dict[str, Any]:
        await repository.create_call_log(
            {
                "customer_id": state["customer_id"],
                "call_id": state.get("call_id"),
                "transcript": state.get("transcript", ""),
                "summary": state.get("summary", ""),
                "outcome": state.get("status", "NEEDS_REVIEW"), # Will now use OpenAI's decision!
                "metadata": state.get("metadata", {})
            }
        )
        return {}

    # 4. UPDATE THE CUSTOMER TABLE
    async def update_customer(state: EvaluationGraphState) -> dict[str, Any]:
        await repository.update_customer_status(state["customer_id"], state["status"])
        return summarize_evaluation(state)

    graph = StateGraph(EvaluationGraphState)
    graph.add_node("evaluate_transcript", evaluate_call)
    graph.add_node("determine_status", determine_status)
    graph.add_node("store_transcript", store_transcript)
    graph.add_node("update_customer", update_customer)
    
    # Notice the new logical ordering of the edges
    graph.add_edge(START, "evaluate_transcript")
    graph.add_edge("evaluate_transcript", "determine_status")
    graph.add_edge("determine_status", "store_transcript")
    graph.add_edge("store_transcript", "update_customer")
    graph.add_edge("update_customer", END)
    
    return graph.compile()


async def run_evaluation_flow(repository, customer_id: str, transcript: str, summary: str, call_id: str | None, metadata: dict[str, Any]) -> dict[str, Any]:
    graph = create_evaluation_graph(repository)
    return await graph.ainvoke(
        {
            "customer_id": customer_id,
            "transcript": transcript,
            "summary": summary,
            "outcome": "NEEDS_REVIEW",
            "confidence": 0.0,
            "status": "NEEDS_REVIEW",
            "call_id": call_id,
            "metadata": metadata,
        }
    )


def build_evaluation_graph() -> dict[str, str]:
    return {"name": "evaluation", "entry": "evaluate_transcript"}


def build_evaluation_prompt(transcript: str) -> str:
    return (
        "Analyze the lead qualification call transcript. Determine whether the customer is 'QUALIFIED', "
        "'NOT_INTERESTED', 'FAILED', or if human review is needed ('NEEDS_REVIEW').\n\n"
        "You MUST return a JSON object with exactly these three keys:\n"
        '- "status": exactly one of ["QUALIFIED", "NOT_INTERESTED", "FAILED", "NEEDS_REVIEW"]\n'
        '- "reason": a short string explaining your decision\n'
        '- "confidence": a float between 0.0 and 1.0 indicating how certain you are\n\n'
        f"Transcript:\n{transcript}"
    )


def apply_low_confidence_rule(result: dict[str, object]) -> dict[str, object]:
    if float(result.get("confidence", 0.0)) < 0.7:
        return {"status": "NEEDS_REVIEW", "reason": result.get("reason", "low confidence"), "confidence": result.get("confidence", 0.0)}
    return result


async def evaluate_transcript(transcript: str) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {"status": "NEEDS_REVIEW", "reason": "OPENAI_API_KEY not configured", "confidence": 0.0}

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = build_evaluation_prompt(transcript)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You analyze lead qualification calls and return JSON only."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)

    result = {
        "status": parsed.get("status", "NEEDS_REVIEW"),
        "reason": parsed.get("reason", ""),
        "confidence": float(parsed.get("confidence", 0.0)),
    }
    return apply_low_confidence_rule(result)


def summarize_evaluation(state: EvaluationGraphState) -> dict[str, object]:
    return {
        "customer_id": state.get("customer_id"),
        "status": state.get("status"),
        "confidence": state.get("confidence", 0.0),
    }