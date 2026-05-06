from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.config import settings


def get_kst_tz() -> ZoneInfo:
    return ZoneInfo(settings.CONTROLLER_TIMEZONE)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def kst_now() -> datetime:
    return datetime.now(get_kst_tz())


def to_utc_naive(dt: datetime) -> datetime:
    """KST-aware datetime → UTC naive datetime (for DB storage)."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def from_utc_naive(dt: datetime) -> datetime:
    """UTC naive datetime (from DB) → KST-aware datetime."""
    return dt.replace(tzinfo=timezone.utc).astimezone(get_kst_tz())


def format_kst(dt: datetime) -> str:
    """DB의 UTC naive datetime을 KST ISO 8601 문자열로 변환."""
    return from_utc_naive(dt).isoformat()
