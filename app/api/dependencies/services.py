from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.payments.services import PaymentsService
from app.db.dao import OutboxEventDAO
from app.db.dao import PaymentDAO
from app.db.session import get_db_session


def get_payments_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PaymentsService:
    """Создает экземпляр payments service."""
    return PaymentsService(
        session=session,
        payment_dao=PaymentDAO(session=session),
        outbox_event_dao=OutboxEventDAO(session=session),
    )
