from fastapi import APIRouter
from starlette_exporter import handle_metrics

router = APIRouter()

router.add_api_route('/metrics', handle_metrics, methods=['GET'], include_in_schema=False)
