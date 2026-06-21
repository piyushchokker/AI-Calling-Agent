import pytest

from app.services.repository import Repository, RepositoryNotFoundError, SupabaseRepository


@pytest.mark.asyncio
async def test_repository_list_companies_uses_pagination(monkeypatch):
    captured = {}

    async def fake_select(self, table, params=None):
        captured["table"] = table
        captured["params"] = params
        return [{"id": "1", "name": "Acme"}]

    monkeypatch.setattr(SupabaseRepository, "select", fake_select)
    repository = Repository()
    companies = await repository.list_companies(limit=5, offset=10)

    assert captured["table"] == "companies"
    assert captured["params"]["limit"] == "5"
    assert captured["params"]["offset"] == "10"
    assert companies[0]["name"] == "Acme"


@pytest.mark.asyncio
async def test_update_customer_status_raises_when_missing(monkeypatch):
    async def fake_select_one(self, table, params):
        return None

    monkeypatch.setattr(SupabaseRepository, "select_one", fake_select_one)
    repository = Repository()

    with pytest.raises(RepositoryNotFoundError):
        await repository.update_customer_status("missing", "QUALIFIED")
