from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import require_tenant_auth
from app.models.schemas import CallLogRead
from app.services.repository import Repository

router = APIRouter()


@router.get("/{customer_id}", response_model=list[CallLogRead])
async def get_call_logs(customer_id: str, _: None = Depends(require_tenant_auth)) -> list[CallLogRead]:
    repository = Repository()
    customer = await repository.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    logs = await repository.get_call_log(customer_id)
    return [CallLogRead.model_validate(log) for log in logs]