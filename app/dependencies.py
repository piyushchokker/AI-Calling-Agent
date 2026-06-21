from fastapi import Header, HTTPException, status

from app.config import settings


def require_tenant_auth(x_tenant_api_key: str | None = Header(default=None, alias="X-Tenant-API-Key")) -> None:
    if not settings.tenant_api_key:
        return
    if not x_tenant_api_key or x_tenant_api_key != settings.tenant_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant credentials")