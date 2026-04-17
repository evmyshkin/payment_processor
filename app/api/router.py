from fastapi import APIRouter

from app.api.extra.controllers.health import router as health_router
from app.api.extra.controllers.metrics import router as metrics_router

router = APIRouter()

# Healthcheck
router.include_router(
    health_router,
    prefix='',
    tags=['Healthcheck'],
)

# Metrics
router.include_router(
    metrics_router,
    prefix='',
    tags=['Metrics'],
)
