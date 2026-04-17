from fastapi import APIRouter
from starlette.responses import JSONResponse
from starlette.responses import Response

router = APIRouter()


@router.get(
    '/health',
    response_model_exclude_none=True,
    summary='Ручка хелсчека.',
    description='Ручка хелсчека.',
)
async def healthcheck() -> Response:
    """Хелсчек.

    Returns:
        InfoResponseSchema:
    """
    return JSONResponse(status_code=200, content={'status': 'ok'})
