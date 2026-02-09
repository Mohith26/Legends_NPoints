from fastapi import APIRouter

from backend.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok"}
