from unittest.mock import AsyncMock

import pytest

from app.consumer.services.webhook_sender import WebhookDeliveryError
from app.consumer.services.webhook_sender import WebhookSender


@pytest.mark.asyncio
async def test_webhook_sender_success_without_retries() -> None:
    post_func = AsyncMock()
    sleep_func = AsyncMock()
    sender = WebhookSender(
        timeout_seconds=5.0,
        max_attempts=3,
        retry_backoff_base_seconds=1.0,
        post_func=post_func,
        sleep_func=sleep_func,
    )

    await sender.send_with_retry(
        webhook_url='https://example.com/hook',
        payload={'status': 'ok'},
    )

    post_func.assert_awaited_once_with('https://example.com/hook', {'status': 'ok'}, 5.0)
    sleep_func.assert_not_awaited()


@pytest.mark.asyncio
async def test_webhook_sender_retries_with_exponential_backoff() -> None:
    attempts = {'count': 0}
    sleep_func = AsyncMock()

    async def flaky_post(_url: str, _payload: dict[str, str], _timeout: float) -> None:
        attempts['count'] += 1
        if attempts['count'] < 3:
            raise RuntimeError('temporary error')

    sender = WebhookSender(
        timeout_seconds=5.0,
        max_attempts=3,
        retry_backoff_base_seconds=1.0,
        post_func=flaky_post,
        sleep_func=sleep_func,
    )

    await sender.send_with_retry(
        webhook_url='https://example.com/hook',
        payload={'status': 'ok'},
    )

    assert attempts['count'] == 3
    assert sleep_func.await_args_list[0].args[0] == 1.0
    assert sleep_func.await_args_list[1].args[0] == 2.0


@pytest.mark.asyncio
async def test_webhook_sender_raises_after_last_attempt() -> None:
    post_func = AsyncMock(side_effect=RuntimeError('network down'))
    sleep_func = AsyncMock()
    sender = WebhookSender(
        timeout_seconds=5.0,
        max_attempts=3,
        retry_backoff_base_seconds=1.0,
        post_func=post_func,
        sleep_func=sleep_func,
    )

    with pytest.raises(WebhookDeliveryError) as exc_info:
        await sender.send_with_retry(
            webhook_url='https://example.com/hook',
            payload={'status': 'ok'},
        )

    assert exc_info.value.__cause__ is None
    assert post_func.await_count == 3
    assert sleep_func.await_args_list[0].args[0] == 1.0
    assert sleep_func.await_args_list[1].args[0] == 2.0
