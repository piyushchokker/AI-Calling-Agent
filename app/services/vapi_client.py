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
            
            # Helper to safely get from either a dict or an object (just in case!)
            def safe_get(obj, key):
                if isinstance(obj, dict):
                    return obj.get(key)
                return getattr(obj, key, None)

            payload = {
            "assistantId": settings.vapi_assistant_id,
            "phoneNumberId": settings.vapi_phone_number_id,
            "customer": {
                "name": safe_get(customer, "name"),
                "number": safe_get(customer, "phone"), 
            },
            "metadata": {
                "customer_id": safe_get(customer, "id"),
                "company_id": safe_get(company, "id"),
            },
            # 👇 Move variableValues inside assistantOverrides 👇
            "assistantOverrides": {
                "variableValues": {
                    "customer_name": safe_get(customer, "name"),
                    "company_name": safe_get(company, "name"),
                    "company_prompt": safe_get(company, "prompt_instructions"),
                    "dynamic_prompt": dynamic_prompt,
                }
            }
        }
            async with await self.create_client() as client:
                response = await client.post("/call", json=payload)

                if response.status_code >= 400:
                    print(f"\n🚨 VAPI ERROR DETAIL: {response.text}\n")


                response.raise_for_status()
                data = response.json()
                return data.get("id") or data.get("call_id")

    async def post_event(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with await self.create_client() as client:
            response = await client.post(path, json=payload)
            response.raise_for_status()
            return response.json()
