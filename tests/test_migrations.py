from importlib import import_module

from app.db.base import Base
from app.db.models.outbox_event import OutboxEvent
from app.db.models.payment import Payment


def test_metadata_contains_expected_tables() -> None:
    table_names = set(Base.metadata.tables)

    assert Payment.__tablename__ in table_names
    assert OutboxEvent.__tablename__ in table_names


def test_initial_migration_module_is_importable() -> None:
    module = import_module('migrations.versions.5f2d5b5a6a8d_add_payments_and_outbox_tables')

    assert module.revision == '5f2d5b5a6a8d'
    assert module.down_revision is None
    assert callable(module.upgrade)
    assert callable(module.downgrade)
