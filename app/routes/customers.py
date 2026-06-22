from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import require_user_auth
from app.models.schemas import CustomerCreate, CustomerRead
from app.services.repository import Repository

router = APIRouter()


@router.get("/", response_model=list[CustomerRead])
async def list_customers(limit: int = Query(default=100, ge=1, le=200), offset: int = Query(default=0, ge=0), token: str = Depends(require_user_auth)) -> list[CustomerRead]:
    repository = Repository(token=token)
    customers = await repository.list_customers(limit=limit, offset=offset)
    return [CustomerRead.model_validate(customer) for customer in customers]


@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(customer: CustomerCreate, token: str = Depends(require_user_auth)) -> CustomerRead:
    repository = Repository(token=token)
    created = await repository.create_customer(customer.model_dump())
    return CustomerRead.model_validate(created)


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(customer_id: str, token: str = Depends(require_user_auth)) -> CustomerRead:
    repository = Repository(token=token)
    customer = await repository.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return CustomerRead.model_validate(customer)
