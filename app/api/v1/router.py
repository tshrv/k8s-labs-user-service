from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.users import router as users_router

v1_router = APIRouter()
v1_router.include_router(health_router, prefix="/health", tags=["Health"])
v1_router.include_router(users_router, prefix="/users", tags=["Users"])
