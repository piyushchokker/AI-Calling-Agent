import pytest

def test_health_route(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_route(client):
    response = client.get("/api/v1/ready")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_company_route_returns_rows(client, monkeypatch):
    from app.services.repository import Repository

    async def fake_list_companies(self, limit=100, offset=0):
        return [{"id": "cmp_1", "name": "Dream Homes Realty", "created_at": None, "updated_at": None}]

    monkeypatch.setattr(Repository, "list_companies", fake_list_companies)
    
    # ADDED: headers parameter with the tenant key
    response = client.get("/api/v1/companies/", headers={"X-Tenant-API-Key": "test_key"})
    
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Dream Homes Realty"


@pytest.mark.asyncio
async def test_customers_route_returns_rows(client, monkeypatch):
    from app.services.repository import Repository

    async def fake_list_customers(self, limit=100, offset=0):
        return [{"id": "cust_1", "company_id": "cmp_1", "name": "John Smith", "phone": "+10000000001", "status": "PENDING", "created_at": None, "updated_at": None}]

    monkeypatch.setattr(Repository, "list_customers", fake_list_customers)
    
    # ADDED: headers parameter with the tenant key
    response = client.get("/api/v1/customers/", headers={"X-Tenant-API-Key": "test_key"})
    
    assert response.status_code == 200
    assert response.json()[0]["status"] == "PENDING"