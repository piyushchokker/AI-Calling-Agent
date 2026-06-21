from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import require_tenant_auth
from app.models.schemas import CampaignCreate, CampaignRead, CampaignStartResponse
from app.graphs.dispatch_graph import run_dispatch_campaign
from app.services.repository import Repository
from app.services.vapi_client import VapiClient

router = APIRouter()


@router.get("/", response_model=list[CampaignRead])
async def list_campaigns(_: None = Depends(require_tenant_auth)) -> list[CampaignRead]:
    return []


@router.post("/", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(campaign: CampaignCreate, _: None = Depends(require_tenant_auth)) -> CampaignRead:
    return CampaignRead(id="0", **campaign.model_dump())


@router.get("/{campaign_id}", response_model=CampaignRead)
async def get_campaign(campaign_id: int, _: None = Depends(require_tenant_auth)) -> CampaignRead:
    return CampaignRead(id=str(campaign_id), company_id="0", name="Example Campaign", objective="Demo")


@router.post("/{company_id}/start", response_model=CampaignStartResponse)
async def start_campaign(company_id: str, _: None = Depends(require_tenant_auth)) -> CampaignStartResponse:
    repository = Repository()
    company = await repository.get_company(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    vapi_client = VapiClient()
    result = await run_dispatch_campaign(repository, vapi_client, company_id)
    return CampaignStartResponse(company_id=company_id, processed_count=result.get("processed_count", 0), errors=result.get("errors", []))
