from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.schemas import CompanyCreate, CompanyRead, CustomerRead
from app.dependencies import require_user_auth
from app.services.repository import Repository, map_repository_error

router = APIRouter()


@router.get("/", response_model=list[CompanyRead])
async def list_companies(limit: int = Query(default=100, ge=1, le=200), offset: int = Query(default=0, ge=0), token: str = Depends(require_user_auth)) -> list[CompanyRead]:
    repository = Repository(token=token)
    companies = await repository.list_companies(limit=limit, offset=offset)
    return [CompanyRead.model_validate(company) for company in companies]


@router.post("/", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(company: CompanyCreate, token: str = Depends(require_user_auth)) -> CompanyRead:
    repository = Repository(token=token)
    created = await repository.create_company(company.model_dump())
    return CompanyRead.model_validate(created)


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(company_id: str, token: str = Depends(require_user_auth)) -> CompanyRead:
    repository = Repository(token=token)
    company = await repository.get_company(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return CompanyRead.model_validate(company)


@router.get("/{company_id}/customers", response_model=list[CustomerRead])
async def list_company_customers(company_id: str, limit: int = Query(default=100, ge=1, le=200), offset: int = Query(default=0, ge=0), token: str = Depends(require_user_auth)) -> list[CustomerRead]:
    repository = Repository(token=token)
    customers = await repository.list_company_customers(company_id, limit=limit, offset=offset)
    return [CustomerRead.model_validate(customer) for customer in customers]
