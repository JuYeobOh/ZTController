from fastapi import APIRouter

from app.schemas import HealthResponse
from app.utils.time import format_kst, utc_now

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", time=format_kst(utc_now()))
