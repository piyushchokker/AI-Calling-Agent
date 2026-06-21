from typing import Any

import httpx

from app.config import settings


class VapiClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or settings.vapi_api_key
        self.base_url = base_url or settings.vapi_base_url

    async def create_client(self) -> httpx.AsyncClient:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=30.0)

    async def create_outbound_call(self, customer: Any, company: Any, dynamic_prompt: str) -> str:
        payload = {
            "assistantId": settings.vapi_assistant_id,
            "phoneNumberId": settings.vapi_phone_number_id,
            "customer": {
                "name": getattr(customer, "name", None),
                "phone": getattr(customer, "phone", None),
            },
            "metadata": {
                "customer_id": getattr(customer, "id", None),
                "company_id": getattr(company, "id", None),
            },
            "variableValues": {
                "customer_name": getattr(customer, "name", None),
                "company_name": getattr(company, "name", None),
                "company_prompt": getattr(company, "prompt_instructions", None),
                "dynamic_prompt": dynamic_prompt,
            },
        }
        async with await self.create_client() as client:
            response = await client.post("/call", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("id") or data.get("call_id")

    async def post_event(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with await self.create_client() as client:
            response = await client.post(path, json=payload)
            response.raise_for_status()
            return response.json()
