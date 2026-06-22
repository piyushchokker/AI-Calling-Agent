from collections.abc import Iterable
from typing import Any, Generic, TypeVar

import httpx
from fastapi import HTTPException, status

from app.config import settings
from app.models import db_models
from app.models.db_models import CallLog, Company, Customer

T = TypeVar("T")


class InMemoryRepository(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []

    def add(self, item: T) -> T:
        self._items.append(item)
        return item

    def all(self) -> list[T]:
        return list(self._items)

    def extend(self, items: Iterable[T]) -> None:
        self._items.extend(items)


class WebhookEventRepository:
    def __init__(self) -> None:
        self._client = SupabaseRepository()

    async def create(self, event_type: str, payload: dict) -> dict[str, Any]:
        return await self._client.insert("webhook_events", {"event_type": event_type, "payload": payload})


class RepositoryError(Exception):
    pass


class RepositoryNotFoundError(RepositoryError):
    pass


class RepositoryUpstreamError(RepositoryError):
    pass


class SupabaseRepository:
    def __init__(self, token: str | None = None) -> None:
        if token:
            # When a token is provided, use the anon key so RLS works based on the token
            api_key = settings.supabase_key
            auth_token = token
        else:
            # Otherwise use the service role key (bypasses RLS)
            api_key = settings.supabase_service_role_key or settings.supabase_key
            auth_token = api_key

        if not settings.supabase_url or not api_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY/SERVICE_ROLE_KEY must be set")
        
        self.base_url = settings.supabase_url.rstrip("/")
        self.headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def _request(self, method: str, path: str, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=30.0) as client:
            try:
                response = await client.request(method, path, params=params, json=json_body)
            except httpx.HTTPError as exc:
                raise RepositoryUpstreamError(str(exc)) from exc
            if response.status_code == status.HTTP_404_NOT_FOUND:
                raise RepositoryNotFoundError(f"Resource not found for {path}")
            if response.status_code >= 400:
                raise RepositoryUpstreamError(response.text or f"Supabase request failed for {path}")
            if response.text:
                return response.json()
            return None

    async def select(self, table: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/rest/v1/{table}", params=params)
        return data or []

    async def select_one(self, table: str, params: dict[str, Any]) -> dict[str, Any] | None:
        rows = await self.select(table, params=params)
        return rows[0] if rows else None

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = await self._request("POST", f"/rest/v1/{table}", json_body=payload)
        if isinstance(data, list):
            return data[0] if data else payload
        return data or payload

    async def update(self, table: str, filters: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        params = {key: f"eq.{value}" for key, value in filters.items()}
        data = await self._request("PATCH", f"/rest/v1/{table}", params=params, json_body=payload)
        if isinstance(data, list):
            return data[0] if data else payload
        return data or payload


class Repository:
    def __init__(self, token: str | None = None) -> None:
        self.supabase = SupabaseRepository(token=token)

    async def create_company(self, payload: dict[str, Any]) -> Company:
        return await self.supabase.insert("companies", payload)

    async def list_companies(self, limit: int = 100, offset: int = 0) -> list[Company]:
        return await self.supabase.select(
            "companies",
            params={"select": "*", "order": "created_at.desc", "limit": str(limit), "offset": str(offset)},
        )

    async def get_company(self, company_id: str) -> Company | None:
        return await self.supabase.select_one("companies", {"id": f"eq.{company_id}", "select": "*"})

    async def create_customer(self, payload: dict[str, Any]) -> Customer:
        return await self.supabase.insert("customers", payload)

    async def get_customer(self, customer_id: str) -> Customer | None:
        return await self.supabase.select_one("customers", {"id": f"eq.{customer_id}", "select": "*"})

    async def list_customers(self, limit: int = 100, offset: int = 0) -> list[Customer]:
        return await self.supabase.select(
            "customers",
            params={"select": "*", "order": "created_at.desc", "limit": str(limit), "offset": str(offset)},
        )

    async def list_company_customers(self, company_id: str, limit: int = 100, offset: int = 0) -> list[Customer]:
        return await self.supabase.select(
            "customers",
            params={"select": "*", "company_id": f"eq.{company_id}", "order": "created_at.desc", "limit": str(limit), "offset": str(offset)},
        )

    async def get_pending_customers(self, company_id: str, limit: int = 100, offset: int = 0) -> list[Customer]:
        return await self.supabase.select(
            "customers",
            params={"select": "*", "company_id": f"eq.{company_id}", "status": "eq.PENDING", "order": "created_at.asc", "limit": str(limit), "offset": str(offset)},
        )

    async def update_customer_status(self, customer_id: str, status: str) -> Customer:
        customer = await self.get_customer(customer_id)
        if not customer:
            raise RepositoryNotFoundError("customer not found")
        return await self.supabase.update("customers", {"id": customer_id}, {"status": status})

    async def create_call_log(self, payload: dict[str, Any]) -> CallLog:
        return await self.supabase.insert("call_logs", payload)

    async def get_call_log(self, customer_id: str) -> list[CallLog]:
        return await self.supabase.select(
            "call_logs",
            params={"select": "*", "customer_id": f"eq.{customer_id}", "order": "created_at.desc"},
        )


def map_repository_error(exc: Exception) -> HTTPException:
    if isinstance(exc, RepositoryNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, RepositoryUpstreamError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Supabase upstream error")
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Repository error")
