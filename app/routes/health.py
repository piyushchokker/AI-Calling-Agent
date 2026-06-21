from fastapi import APIRouter

from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=HealthResponse, tags=["health"])
def readiness_check() -> HealthResponse:
    return HealthResponse()
