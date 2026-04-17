from fastapi import APIRouter
from fastapi import Depends

from app.api.dependencies.auth import require_api_key
from app.api.extra.controllers.health import router as health_router
from app.api.extra.controllers.metrics import router as metrics_router
from app.api.v1.payments.controllers.payments_controller import router as payments_router

router = APIRouter(dependencies=[Depends(require_api_key)])

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

# Payments v1
router.include_router(
    payments_router,
    prefix='/api/v1/payments',
    tags=['Payments'],
)
