from fastapi import APIRouter, status
from sqlalchemy import text

from app.dependencies import DbSession

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/db", status_code=status.HTTP_200_OK)
async def db_health_check(db: DbSession) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
